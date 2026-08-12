"""
overlay.py — 游戏内悬浮状态框

架构:
  run.py / directx.py  →  OverlayClient (写 JSON)  →  ./logs/overlay_status.json
                                                              ↓ (300ms 轮询)
  overlay_main.py  →  OverlayWindow (读 JSON, 渲染窗口)

OverlayClient  — 轻量, 供 run.py 进程内调用, 只写状态文件
OverlayWindow  — 完整 Win32 窗口, 由 overlay_main.py 独立进程使用

通信文件: ./logs/overlay_status.json
  { "phase": str, "rounds": int, "success": int, "running": bool, "exit": bool }

退出协议:
  - 正常: run.py 退出前调 overlay.stop() → exit=true → overlay_main 检测后关闭
  - 崩溃: status.json 超过 15 秒未更新 → overlay_main 自动退出
"""

import json
import os
import time
import traceback
from pathlib import Path


# 状态文件路径
STATUS_PATH = Path("./logs/overlay_status.json")
ERROR_LOG = Path("./logs/overlay_error.log")

# 心跳超时 (秒) — 超过此时间 status.json 未更新则认为 run.py 已死
HEARTBEAT_TIMEOUT = 15.0


def _log_error(msg):
    """写错误日志 (追加模式)"""
    try:
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


# ============================================================
# OverlayClient — 状态发布端 (run.py 进程内使用)
# ============================================================

class OverlayClient:
    """轻量客户端 — 只写 JSON 状态文件, 不创建窗口"""

    def __init__(self):
        self._state = {
            "phase": "等待启动",
            "rounds": 0,
            "success": 0,
            "running": False,
            "exit": False,
        }
        self._started = False

    def start(self):
        """初始化状态文件 (仅一次)"""
        if self._started:
            return
        self._started = True
        try:
            STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self._write()

    def update(self, phase=None, rounds=None, success=None, running=None):
        """更新状态并写入文件 (每次调用都刷新 mtime, 兼作心跳)"""
        if phase is not None:
            self._state["phase"] = phase
        if rounds is not None:
            self._state["rounds"] = rounds
        if success is not None:
            self._state["success"] = success
        if running is not None:
            self._state["running"] = running
        if self._started:
            self._write()

    def stop(self):
        """通知 overlay_main 进程退出"""
        self._state["exit"] = True
        if self._started:
            self._write()

    def _write(self):
        """原子写入: 先写 .tmp 再 rename, 防止读端读到半写数据"""
        try:
            tmp = STATUS_PATH.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False)
            os.replace(tmp, STATUS_PATH)
        except Exception:
            pass


# 全局单例 (供 run.py / directx.py 使用)
overlay = OverlayClient()


# ============================================================
# 以下为 OverlayWindow — 独立进程使用 (由 overlay_main.py 导入)
# ============================================================

import ctypes
import ctypes.wintypes as wintypes


# --- Win32 常量 ---
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001

WM_PAINT = 0x000F
WM_TIMER = 0x0113
WM_DESTROY = 0x0002

LWA_COLORKEY = 0x00000001

TRANSPARENT = 1

DT_LEFT = 0x0000
DT_TOP = 0x0000
DT_NOCLIP = 0x0100

FW_BOLD = 700
DEFAULT_QUALITY = 0
OUT_DEFAULT_PRECIS = 0
CLIP_DEFAULT_PRECIS = 0
DEFAULT_CHARSET = 1
FF_SWISS = 0x20

PS_SOLID = 0

TIMER_ID = 1
TIMER_INTERVAL = 300  # ms

# 颜色 (BGR for COLORREF)
COLOR_KEY = 0x00FF00FF      # 紫红 — 透明色键
COLOR_BG = 0x0018280D       # 深绿背景 #0D2818
COLOR_BORDER = 0x0000CC00   # 亮绿边框 #00CC00
COLOR_TEXT = 0x0066FF00     # 亮绿文字 #00FF66

WIN_W = 260
WIN_H = 72
WIN_X = 10
WIN_Y = 10


# --- Win32 结构体 ---

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, wintypes.HWND, wintypes.UINT,
    wintypes.WPARAM, wintypes.LPARAM
)


# --- 加载 Win32 库 ---
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
    wintypes.DWORD, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU,
    wintypes.HINSTANCE, ctypes.c_void_p
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD
]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL

user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.BeginPaint.restype = wintypes.HDC

user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.EndPaint.restype = wintypes.BOOL

user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL

user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]
user32.InvalidateRect.restype = wintypes.BOOL

user32.SetTimer.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.UINT, ctypes.c_void_p]
user32.SetTimer.restype = wintypes.UINT

user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
]
user32.GetMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_long

user32.DefWindowProcW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.DefWindowProcW.restype = ctypes.c_long

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL

gdi32.CreateFontW.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.LPCWSTR
]
gdi32.CreateFontW.restype = wintypes.HFONT

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetTextColor.restype = wintypes.COLORREF

gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int

gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH

user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
user32.FillRect.restype = ctypes.c_int

user32.DrawTextW.argtypes = [
    wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int,
    ctypes.POINTER(wintypes.RECT), wintypes.UINT
]
user32.DrawTextW.restype = ctypes.c_int

gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
gdi32.CreatePen.restype = wintypes.HPEN

gdi32.Rectangle.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
gdi32.Rectangle.restype = wintypes.BOOL


class OverlayWindow:
    """悬浮框窗口 — 由 overlay_main.py 独立进程使用

    每 300ms 从 ./logs/overlay_status.json 读取状态并重绘。
    检测到 exit=true 或心跳超时后自动关闭。

    关键修复:
    - GDI 对象 (font/brush/pen) 在 run() 中创建一次, 消息循环结束后统一释放
    - WndProc 回调整体 try/except, 任何异常写日志但不崩溃
    """

    def __init__(self):
        self._state = {
            "phase": "等待启动",
            "rounds": 0,
            "success": 0,
            "running": False,
            "exit": False,
        }
        self._file_mtime = 0.0
        self._heartbeat = time.time()
        self._hwnd = None
        # GDI 对象 — 在 run() 中创建, 循环结束后释放
        self._font = None
        self._brush = None
        self._pen = None
        self._wnd_proc_ref = None
        self._class_brush = None  # 窗口类背景画刷 (注册时传入, 循环结束后释放)

    def run(self):
        """创建窗口并运行消息循环 (阻塞)"""
        _log_error("OverlayWindow.run() 开始")

        class_name = "D2OverlayClass"
        window_name = "D2Overlay"

        hInstance = kernel32.GetModuleHandleW(None)

        # --- 创建 GDI 对象 (仅一次) ---
        self._font = gdi32.CreateFontW(
            15, 0, 0, 0, FW_BOLD,
            0, 0, 0,
            DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS,
            CLIP_DEFAULT_PRECIS,
            DEFAULT_QUALITY,
            FF_SWISS,
            "Consolas"
        )
        self._brush = gdi32.CreateSolidBrush(COLOR_BG)
        self._pen = gdi32.CreatePen(PS_SOLID, 1, COLOR_BORDER)
        self._class_brush = gdi32.CreateSolidBrush(COLOR_BG)

        if not self._font or not self._brush or not self._pen:
            _log_error(f"GDI 对象创建失败: font={self._font} brush={self._brush} pen={self._pen}")

        def wnd_proc(hwnd, msg, wparam, lparam):
            """WndProc — 所有异常在此捕获, 绝不让异常穿过 C 回调边界"""
            try:
                if msg == WM_PAINT:
                    self._on_paint(hwnd)
                    return 0
                elif msg == WM_TIMER:
                    self._load_status()
                    if self._should_exit():
                        user32.DestroyWindow(hwnd)
                        return 0
                    user32.InvalidateRect(hwnd, None, False)
                    return 0
                elif msg == WM_DESTROY:
                    user32.PostQuitMessage(0)
                    return 0
            except Exception as e:
                _log_error(f"WndProc 异常 (msg={msg}): {e}\n{traceback.format_exc()}")
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wnd_proc_ref = WNDPROC(wnd_proc)

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = ctypes.cast(self._wnd_proc_ref, ctypes.c_void_p)
        wc.hInstance = hInstance
        wc.hbrBackground = self._class_brush
        wc.lpszClassName = class_name

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if atom == 0:
            err = kernel32.GetLastError()
            _log_error(f"RegisterClassEx 失败, GetLastError={err}")
            self._cleanup_gdi()
            return

        ex_style = (WS_EX_LAYERED | WS_EX_TRANSPARENT |
                    WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
        style = WS_POPUP | WS_VISIBLE

        self._hwnd = user32.CreateWindowExW(
            ex_style, class_name, window_name, style,
            WIN_X, WIN_Y, WIN_W, WIN_H,
            None, None, hInstance, None
        )
        if self._hwnd == 0:
            err = kernel32.GetLastError()
            _log_error(f"CreateWindowEx 失败, GetLastError={err}")
            self._cleanup_gdi()
            return

        user32.SetLayeredWindowAttributes(
            self._hwnd, COLOR_KEY, 255, LWA_COLORKEY
        )

        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        user32.SetWindowPos(
            self._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )

        user32.SetTimer(self._hwnd, TIMER_ID, TIMER_INTERVAL, None)

        # 首次加载状态
        self._load_status()
        _log_error("窗口创建成功, 进入消息循环")

        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            _log_error(f"消息循环异常: {e}\n{traceback.format_exc()}")

        _log_error("消息循环结束, 清理资源")
        self._cleanup_gdi()
        _log_error("OverlayWindow.run() 结束")

    def _cleanup_gdi(self):
        """释放所有 GDI 对象"""
        for obj_attr in ("_font", "_brush", "_pen", "_class_brush"):
            obj = getattr(self, obj_attr, None)
            if obj:
                try:
                    gdi32.DeleteObject(obj)
                except Exception:
                    pass
                setattr(self, obj_attr, None)

    def _load_status(self):
        """从 JSON 文件加载状态 (mtime 变化时才读, 并刷新心跳)"""
        try:
            if not STATUS_PATH.exists():
                return
            mtime = STATUS_PATH.stat().st_mtime
            if mtime == self._file_mtime:
                return
            self._file_mtime = mtime
            self._heartbeat = time.time()
            with open(STATUS_PATH, "r", encoding="utf-8") as f:
                self._state = json.load(f)
        except Exception as e:
            _log_error(f"_load_status 异常: {e}")

    def _should_exit(self):
        """检查是否应该退出"""
        if self._state.get("exit", False):
            return True
        if time.time() - self._heartbeat > HEARTBEAT_TIMEOUT:
            _log_error(f"心跳超时: {time.time() - self._heartbeat:.1f}s > {HEARTBEAT_TIMEOUT}s")
            return True
        return False

    def _get_text(self):
        state = "● 运行中" if self._state.get("running") else "○ 待命"
        return f"{state}  R:{self._state.get('rounds', 0)}  OK:{self._state.get('success', 0)}\n{self._state.get('phase', '')}"

    def _on_paint(self, hwnd):
        """绘制窗口内容 — 使用预创建的 GDI 对象, 不在 paint 中创建/销毁"""
        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
        if not hdc:
            return

        try:
            # 用预创建的 brush + pen 画背景矩形
            old_brush = gdi32.SelectObject(hdc, self._brush)
            old_pen = gdi32.SelectObject(hdc, self._pen)
            gdi32.Rectangle(hdc, 0, 0, WIN_W, WIN_H)
            gdi32.SelectObject(hdc, old_brush)
            gdi32.SelectObject(hdc, old_pen)

            # 绘制文字
            if self._font:
                old_font = gdi32.SelectObject(hdc, self._font)
                gdi32.SetTextColor(hdc, COLOR_TEXT)
                gdi32.SetBkMode(hdc, TRANSPARENT)

                text = self._get_text()

                text_rect = wintypes.RECT()
                text_rect.left = 8
                text_rect.top = 5
                text_rect.right = WIN_W - 8
                text_rect.bottom = WIN_H - 5

                user32.DrawTextW(
                    hdc, text, -1,
                    ctypes.byref(text_rect),
                    DT_LEFT | DT_TOP | DT_NOCLIP
                )

                gdi32.SelectObject(hdc, old_font)
        except Exception as e:
            _log_error(f"_on_paint 异常: {e}\n{traceback.format_exc()}")
        finally:
            user32.EndPaint(hwnd, ctypes.byref(ps))
