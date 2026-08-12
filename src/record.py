"""
录制工具 v3 — mss 高速截图 + OpenCV 视频输出，不拦截任何输入。

操作:
    1. 双击 record.bat 启动
    2. 切到游戏窗口
    3. 按 F8 开始录制（蜂鸣一声）
    4. 手动完成一次完整踢 Boss
    5. 按 F8 停止（蜂鸣两声）
    6. 按 F9 退出

输出: ./recordings/{session_id}/
    - recording.mp4     视频（可直接播放观看）
    - timeline.json     键盘+鼠标时间轴
"""

import ctypes
import json
import sys
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from mss import MSS

# ===== 路径 =====
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "recordings"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ===== 录制参数 =====
RECORD_FPS = 10                          # 视频帧率
FRAME_INTERVAL = 1.0 / RECORD_FPS        # 帧间隔
VIDEO_CODEC = "mp4v"                     # OpenCV 编码器


# ===== Win32 API =====
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def key_down(vk_code: int) -> bool:
    return (user32.GetAsyncKeyState(vk_code) & 0x8000) != 0


def get_cursor_pos() -> tuple[int, int]:
    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


def beep(freq: int, duration_ms: int):
    try:
        kernel32.Beep(freq, duration_ms)
    except Exception:
        pass


def set_console_title(text: str):
    try:
        user32.SetConsoleTitleW(text)
    except Exception:
        pass


# ===== 虚拟键码 =====
VK_CODES = {
    "F8": 0x77, "F9": 0x78,
    "W": 0x57, "A": 0x41, "S": 0x53, "D": 0x44,
    "Q": 0x51, "E": 0x45, "R": 0x52, "F": 0x46,
    "G": 0x47, "V": 0x56, "C": 0x43, "X": 0x58,
    "Z": 0x5A, "T": 0x54,
    "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "SHIFT": 0x10, "CTRL": 0x11, "SPACE": 0x20,
    "LCLICK": 0x01, "RCLICK": 0x02,
    "TAB": 0x09, "ESC": 0x1B,
}


def log(msg: str):
    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{now}] {msg}")


def record():
    print("=" * 56)
    print("  D2 录制工具 v3 — 输出 MP4 视频 + 操作时间轴")
    print("=" * 56)
    print("  F8 = 开始/停止录制")
    print("  F9 = 退出程序")
    print("-" * 56)
    print()
    log(f"输出目录: {OUTPUT_DIR}")
    log("切换到游戏窗口后，按 F8 开始录制...")
    print()

    sct = MSS()
    monitor = sct.monitors[1]  # 主显示器
    screen_w = monitor["width"]
    screen_h = monitor["height"]
    log(f"屏幕尺寸: {screen_w}x{screen_h}")

    # 读取游戏分辨率（从 settings.toml）
    game_w = screen_w
    game_h = screen_h
    try:
        import tomllib
        settings = tomllib.loads((BASE_DIR / "settings.toml").read_text("utf-8"))
        res = settings.get("base", {}).get("resolution", "")
        if res == "1080p":
            game_w, game_h = 1920, 1080
        elif res == "1440p":
            game_w, game_h = 2560, 1440
    except Exception:
        pass
    log(f"游戏分辨率: {game_w}x{game_h} (from settings.toml)")

    session = None
    session_dir = None
    recording = False
    video_writer = None
    start_time = 0.0
    frame_idx = 0
    timeline = []
    prev_keys = set()
    prev_mouse = 0
    last_f8_time = 0.0

    while True:
        now = time.perf_counter()

        f8 = key_down(VK_CODES["F8"])
        f9 = key_down(VK_CODES["F9"])

        if f9:
            log("F9 退出")
            break

        if f8 and now - last_f8_time > 1.0:
            last_f8_time = now
            if recording:
                # ─── 停止录制 ───
                recording = False
                if video_writer:
                    video_writer.release()
                    video_writer = None

                duration = int((now - start_time) * 1000)
                timeline_path = session_dir / "timeline.json"
                out = {
                    "session_id": session,
                    "recorded_at": datetime.now().isoformat(),
                    "screen": f"{screen_w}x{screen_h}",
                    "game_resolution": f"{game_w}x{game_h}",
                    "fps": RECORD_FPS,
                    "duration_ms": duration,
                    "total_frames": frame_idx,
                    "events": len(timeline),
                    "timeline": timeline,
                }
                timeline_path.write_text(
                    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
                )

                video_path = session_dir / "recording.mp4"
                video_mb = video_path.stat().st_size / (1024 * 1024) if video_path.exists() else 0
                print()
                print("=" * 56)
                print(f"  录制完成！")
                print(f"  时长: {duration // 1000}s  帧数: {frame_idx}  事件: {len(timeline)}")
                print(f"  视频: {video_path.name} ({video_mb:.1f} MB)")
                print(f"  时间轴: timeline.json")
                print(f"  目录: {session_dir}")
                print("=" * 56)
                print()
                beep(800, 100)
                time.sleep(0.1)
                beep(800, 100)
                set_console_title("[已停止] D2 录制")

            else:
                # ─── 开始录制 ───
                session = datetime.now().strftime("%Y%m%d_%H%M%S")
                session_dir = OUTPUT_DIR / session
                session_dir.mkdir(parents=True, exist_ok=True)

                # 创建视频写入器
                video_path = session_dir / "recording.mp4"
                fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
                video_writer = cv2.VideoWriter(
                    str(video_path),
                    fourcc,
                    RECORD_FPS,
                    (screen_w, screen_h),
                )
                if not video_writer.isOpened():
                    log("错误: 无法创建视频文件，尝试用 avc1 编码...")
                    video_writer = cv2.VideoWriter(
                        str(video_path),
                        cv2.VideoWriter_fourcc(*"avc1"),
                        RECORD_FPS,
                        (screen_w, screen_h),
                    )
                if not video_writer.isOpened():
                    log("错误: 视频编码失败，回退到 avi 格式...")
                    avi_path = session_dir / "recording.avi"
                    video_writer = cv2.VideoWriter(
                        str(avi_path),
                        cv2.VideoWriter_fourcc(*"XVID"),
                        RECORD_FPS,
                        (screen_w, screen_h),
                    )

                recording = True
                start_time = now
                frame_idx = 0
                timeline = []
                prev_keys = set()
                prev_mouse = 0

                print()
                print("=" * 56)
                print(f"  [录制中] {session}")
                print(f"  分辨率: {screen_w}x{screen_h}  FPS: {RECORD_FPS}")
                print("  按 F8 停止  |  F9 退出")
                print("=" * 56)
                beep(1000, 200)
                set_console_title(f"[录制中] {session}")

        if not recording:
            time.sleep(0.1)
            continue

        # ─── 录制一帧 ───
        offset_ms = int((now - start_time) * 1000)

        # 截图（mss 返回 BGRA numpy 数组）
        try:
            img = np.array(sct.grab(monitor))
            # mss 返回 BGRA → 转 BGR 给 OpenCV
            frame_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            video_writer.write(frame_bgr)
        except Exception as e:
            log(f"  [截图失败] {e}")

        # 检测按键变化
        curr_keys = set()
        for name, vk in VK_CODES.items():
            if name in ("F8", "F9"):
                continue
            if key_down(vk):
                curr_keys.add(name)

        for k in curr_keys - prev_keys:
            if k in ("LCLICK", "RCLICK"):
                continue  # 鼠标单独处理
            timeline.append({
                "time_ms": offset_ms,
                "type": "key",
                "action": "press",
                "key": k,
            })
            log(f"  [{offset_ms:6d}ms] 按下 {k}")

        for k in prev_keys - curr_keys:
            if k in ("LCLICK", "RCLICK"):
                continue
            timeline.append({
                "time_ms": offset_ms,
                "type": "key",
                "action": "release",
                "key": k,
            })

        # 鼠标点击
        curr_mouse = 0
        if key_down(VK_CODES["LCLICK"]):
            curr_mouse |= 1
        if key_down(VK_CODES["RCLICK"]):
            curr_mouse |= 2

        if curr_mouse & 1 and not prev_mouse & 1:
            x, y = get_cursor_pos()
            timeline.append({
                "time_ms": offset_ms,
                "type": "click",
                "action": "press",
                "button": "left",
                "x": x,
                "y": y,
            })
            log(f"  [{offset_ms:6d}ms] 左键 @ ({x}, {y})")
        if not curr_mouse & 1 and prev_mouse & 1:
            timeline.append({
                "time_ms": offset_ms,
                "type": "click",
                "action": "release",
                "button": "left",
            })
        if curr_mouse & 2 and not prev_mouse & 2:
            x, y = get_cursor_pos()
            timeline.append({
                "time_ms": offset_ms,
                "type": "click",
                "action": "press",
                "button": "right",
                "x": x,
                "y": y,
            })
            log(f"  [{offset_ms:6d}ms] 右键 @ ({x}, {y})")
        if not curr_mouse & 2 and prev_mouse & 2:
            timeline.append({
                "time_ms": offset_ms,
                "type": "click",
                "action": "release",
                "button": "right",
            })

        # 鼠标移动（每5帧记录一次节省空间）
        if frame_idx % 5 == 0:
            x, y = get_cursor_pos()
            timeline.append({
                "time_ms": offset_ms,
                "type": "cursor",
                "x": x,
                "y": y,
            })

        prev_keys = curr_keys
        prev_mouse = curr_mouse
        frame_idx += 1

        # 控制帧率
        elapsed = time.perf_counter() - now
        if elapsed < FRAME_INTERVAL:
            time.sleep(FRAME_INTERVAL - elapsed)

        # 进度提示
        if frame_idx % 50 == 0:
            log(f"  ... {frame_idx} 帧 ({offset_ms // 1000}s)")

    # 清理
    if video_writer:
        video_writer.release()
    sct.close()

    log("录制工具已退出")


if __name__ == "__main__":
    try:
        record()
    except KeyboardInterrupt:
        print()
        log("Ctrl+C 停止")
    except Exception as e:
        print(f"未预期错误: {e}")
        import traceback
        traceback.print_exc()
