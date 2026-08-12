"""
directx.py — 棱镜虚空猎踢Boss动作函数

飞升前序列严格按 .rec 录制逐帧回放，确保走位零偏差。
飞升后战斗基于 888888888888888888888888888.rec 录制流程重构（近战版）。

完整流程:
  1. pre_ascension_sequence() — W定位→A定位→E插旗→E吃旗→2切武器→冲刺→D/A走位→SPACE跳
  2. use_ascension() — X飞升→等待动画
  3. post_ascension_combat() — S后退→ADS瞄准+C近战→F超能→冲刺+G终结
"""

import time
import pydirectinput
from pydirectinput import (
    keyDown,
    keyUp,
    leftClick,
    move,
    moveTo,
    mouseDown,
    mouseUp,
    RIGHT,
    press,
)
from loguru import logger

from size import get_resize
from settings import monitor_settings, base_settings

pydirectinput.PAUSE = 0


# ============================================================
# 工具函数
# ============================================================

class AbortError(Exception):
    """用户中止信号 — 不应触发 self_kill"""
    pass


def press_and_hold_key(key: str, seconds: float):
    """按住按键一段时间"""
    keyDown(key)
    time.sleep(seconds)
    keyUp(key)


def sprint_forward(seconds: float):
    """按住 Shift+W 向前冲刺"""
    keyDown("shiftleft")
    time.sleep(0.01)
    keyDown("w")
    time.sleep(seconds)
    keyUp("w")
    keyUp("shiftleft")


def turn_camera(offset: tuple, step_px: int = 30):
    """
    分步移动鼠标模拟镜头转动。
    大偏移量(>100px)在游戏中一次 move() 会不准，
    拆成小步(默认30px/步)逐步移动，5ms间隔，模拟真实鼠标。
    """
    dx, dy = int(offset[0]), int(offset[1])
    if dx == 0 and dy == 0:
        return

    total_dist = max(abs(dx), abs(dy))
    steps = max(1, total_dist // step_px)
    step_x = dx / steps
    step_y = dy / steps

    for i in range(steps):
        # 用累积方式避免浮点舍入误差
        cur_x = int((i + 1) * step_x) - int(i * step_x)
        cur_y = int((i + 1) * step_y) - int(i * step_y)
        if cur_x != 0 or cur_y != 0:
            move(cur_x, cur_y, relative=True)
        time.sleep(0.005)

    time.sleep(0.1)


# ============================================================
# 阶段0-4: 飞升前完整序列（严格按 .rec 录制逐帧回放）
# ============================================================

# 全局中止标志 (run.py 设为 True 时中止序列)
_abort = False

def set_abort(flag: bool):
    """设置中止标志"""
    global _abort
    _abort = flag


def pre_ascension_sequence():
    """
    严格按 .rec 录制回放飞升(X)前的所有键盘操作。
    基于 D:\\脚本\\888888888888888888888888888.rec 录制 (2026-08-09)。
    总时长 ~17.8 秒。

    时间轴 (秒):
      0.000-0.359    W 轻点定位 (359ms)
      0.718-1.172    A 轻点定位 (454ms)
      1.859-2.718    E 插旗 (859ms)
      4.703-5.265    E 吃旗 (562ms)
      5.672-5.812    按2 切武器
      5.953-6.078    按2 切武器 (二次确认)
      7.656          W down (开始冲刺)
      8.343-8.500    SHIFT 短冲刺 (157ms)
      10.109-12.125  D 侧移右 (2016ms)
      13.015-13.312  D 短按 (297ms)
      15.406-16.218  A 侧移左 (812ms)
      16.422-16.609  A 短按 (187ms)
      17.422         W up (停止冲刺, W按住9766ms)
      17.625-17.781  SPACE 跳跃 (156ms)
      18.031         → X 飞升 (由 use_ascension() 执行)
    """
    logger.info("🎬 开始回放飞升前序列 (17.8s)...")
    global _abort
    _abort = False

    start = time.monotonic()

    def at(t_sec):
        if _abort:
            raise AbortError("用户中止")
        elapsed = time.monotonic() - start
        if t_sec > elapsed:
            time.sleep(t_sec - elapsed)

    # === W 轻点定位 (0-0.359s) ===
    keyDown("w")
    at(0.359)
    keyUp("w")

    # === A 轻点定位 (0.718-1.172s) ===
    at(0.718)
    keyDown("a")
    at(1.172)
    keyUp("a")

    # === E 插旗 (1.859-2.718s) ===
    at(1.859)
    keyDown(base_settings.插旗按键)
    at(2.718)
    keyUp(base_settings.插旗按键)
    logger.info("  ✓ 旗帜已放置")

    # === E 吃旗 (4.703-5.265s) ===
    at(4.703)
    keyDown(base_settings.插旗按键)
    at(5.265)
    keyUp(base_settings.插旗按键)
    logger.info("  ✓ 吃旗完成 (弹药+超能已满)")

    # === 按2 切武器 ×2 (5.672-6.078s) ===
    at(5.672)
    press("2")
    at(5.953)
    press("2")
    logger.info("  ✓ 切2号武器")

    # === W+SHIFT 冲刺进场地 (7.656s起) ===
    at(7.656)
    keyDown("w")

    # SHIFT 短冲刺
    at(8.343)
    keyDown("shiftleft")
    at(8.500)
    keyUp("shiftleft")

    # D 侧移右 (2016ms)
    at(10.109)
    keyDown("d")
    at(12.125)
    keyUp("d")

    # D 短按 (297ms)
    at(13.015)
    keyDown("d")
    at(13.312)
    keyUp("d")

    # A 侧移左 (812ms)
    at(15.406)
    keyDown("a")
    at(16.218)
    keyUp("a")

    # A 短按 (187ms)
    at(16.422)
    keyDown("a")
    at(16.609)
    keyUp("a")

    # W up (W总共按住9766ms)
    at(17.422)
    keyUp("w")

    # === SPACE 跳跃 ===
    at(17.625)
    keyDown("space")
    at(17.781)
    keyUp("space")
    logger.info("  ✓ 跳跃完成，准备飞升")

    # 等到飞升时刻 (录制中X在18.031s, 距SPACE up 250ms)
    at(18.031)

    logger.success("飞升前序列完成 (总时长18.0s)")


def release_all_movement_keys():
    """释放所有可能处于按下状态的移动键和鼠标 — 在中止时调用"""
    from settings import base_settings as _bs
    keys = ["w", "a", "s", "d", "shiftleft", "space", _bs.插旗按键, _bs.终结技按键, _bs.近战按键]
    for key in keys:
        try:
            keyUp(key)
        except Exception:
            pass
    try:
        mouseUp(button=RIGHT)
    except Exception:
        pass


# ============================================================
# 阶段1: 飞升
# ============================================================

def use_ascension():
    """按X飞升 + 等待动画"""
    logger.info("🦅 X 飞升分身...")
    press(base_settings.飞升按键)
    time.sleep(monitor_settings.飞升后等待)
    logger.success("分身已放置，Boss已开怪")


# ============================================================
# 阶段2: 飞升后完整战斗序列 (基于 9999999.rec 录制)
# ============================================================

def post_ascension_combat():
    """
    飞升后完整战斗序列，基于 888888888888888888888888888.rec 录制流程（近战版）。
    用C近战替代枪射击，ADS+近战→F超能→冲刺+G终结。

    录制时间轴 (相对S down, 即飞升后第一个动作):
      0.000-0.594   S×2 后退定位
      2.109         RMB down (ADS)
      2.125-3.406   ADS中鼠标左转 (-1512, +33)
      4.047         C 近战 (ADS中)
      4.094         RMB up
      4.125         C up
      7.625-8.547   超能前瞄准 (+265, +23)
      8.563-8.688   F 超能
      10.375        A down (冲刺前侧移)
      10.500        W down (冲刺)
      10.578        SHIFT down
      10.734-11.484 G×4 连按 (A up@11.047, W up@11.500, SHIFT up@11.516)

    可调参数 (settings.toml + tuner.py):
      飞升后等待        — X飞升→S后退间隔
      第一次ADS偏移      — ① C近战前瞄准
      近战前等待         — ADS瞄准后→C近战前额外等待(等怪出现)
      第一次ADS后等待    — 近战释放→超能前瞄准间隔
      超能前瞄准偏移     — ② F超能前瞄准
      超能后等待         — F→冲刺间隔
      冲刺A时间          — 冲刺前A侧移持续时间
      冲刺瞄准偏移       — 冲刺中鼠标微调
      冲刺到终结时间     — 冲刺→G终结间隔
      终结后等待         — G后等待
    """
    logger.info("⚔️ 飞升后战斗序列开始 (近战版)...")

    start = time.monotonic()

    def at(t_sec):
        """等待到相对开始时间的 t_sec 秒"""
        if _abort:
            raise AbortError("用户中止")
        elapsed = time.monotonic() - start
        if t_sec > elapsed:
            time.sleep(t_sec - elapsed)

    # === S×2 后退定位 (0-0.594s) ===
    logger.info("🏃 S后退定位...")
    keyDown("s")
    at(0.188)
    keyUp("s")
    at(0.469)
    keyDown("s")
    at(0.594)
    keyUp("s")

    # === ① 第一次ADS + 瞄准 + C近战 ===
    logger.info("🎯 ① 第一次ADS瞄准...")
    at(2.109)
    mouseDown(button=RIGHT)

    # ① 瞄准 (录制: 左转 -1512, +33)
    at(2.125)
    turn_camera(monitor_settings.第一次ADS偏移, step_px=10)

    # 等待到C近战时刻 (录制: aim结束@3.406, C@4.047)
    at(4.047)
    # 近战前额外等待 (等怪出现)
    if monitor_settings.近战前等待 > 0:
        time.sleep(monitor_settings.近战前等待)
    logger.info("👊 第一次近战!")
    keyDown(base_settings.近战按键)
    at(4.094)
    mouseUp(button=RIGHT)
    at(4.125)
    keyUp(base_settings.近战按键)

    # === 第一次ADS后等待 → 超能前瞄准 ===
    wait_1to_aim = monitor_settings.第一次ADS后等待 - (4.125 - 2.109)
    if wait_1to_aim > 0:
        at(2.109 + monitor_settings.第一次ADS后等待)

    # === ② 超能前瞄准 ===
    if monitor_settings.超能前瞄准偏移 != (0, 0):
        logger.info("🔧 ③ 超能前瞄准...")
        turn_camera(monitor_settings.超能前瞄准偏移, step_px=10)

    # === F 超能 ===
    logger.info("🏹 释放虚空超能!")
    press(base_settings.超能按键)

    # === 超能后等待 → 冲刺 ===
    time.sleep(monitor_settings.超能后等待)

    # === 冲刺 + G终结 ===
    logger.info("💨 冲刺!")
    keyDown("a")      # 侧移 (录制: A在W前125ms)
    time.sleep(monitor_settings.冲刺A时间)
    keyDown("w")
    time.sleep(0.078)
    keyDown("shiftleft")

    # 冲刺中鼠标微调 (可调)
    if monitor_settings.冲刺瞄准偏移 != (0, 0):
        logger.info("🔧 冲刺中微调...")
        turn_camera(monitor_settings.冲刺瞄准偏移, step_px=5)

    # 冲刺到终结时间后开始G连按
    time.sleep(monitor_settings.冲刺到终结时间)

    # G连按×4 (录制: 4次, 每次约120-150ms间隔)
    logger.info("💀 G终结技连按!")
    for i in range(4):
        keyDown(base_settings.终结技按键)
        time.sleep(0.14)
        keyUp(base_settings.终结技按键)
        if i < 3:
            time.sleep(0.06)

    # 释放移动键
    keyUp("a")
    keyUp("w")
    keyUp("shiftleft")

    # 终结后等待
    time.sleep(monitor_settings.终结后等待)

    logger.success("战斗序列完成!")


# ============================================================
# 地图 / 副本操作
# ============================================================

def open_map_and_select_dungeon():
    """打开地图 → 选择战争领主的废墟 → 选择大师难度"""
    press("m")
    time.sleep(1)
    moveTo(*get_resize(2360))
    time.sleep(0.3)
    leftClick()
    time.sleep(1.5)
    moveTo(*get_resize(1960, 1110))
    time.sleep(0.3)
    leftClick()
    time.sleep(1.5)
    moveTo(*get_resize(455, 460))
    time.sleep(0.3)
    leftClick()


def start_next_round():
    """重新开始副本"""
    open_map_and_select_dungeon()
    time.sleep(2)
    moveTo(*get_resize(2180, 1210))
    time.sleep(0.3)
    leftClick()


def reset_checkpoint():
    """
    重置副本进度：ESC → 更改角色 → 登录 → 重新进入。
    坐标已校准为录制实测值 (717,600) 和 (1237,647)。
    """
    logger.info("🔄 重置副本进度...")
    press("esc")
    time.sleep(monitor_settings.打开菜单后等待)

    moveTo(*monitor_settings.更改角色坐标)
    time.sleep(0.3)
    leftClick()
    time.sleep(monitor_settings.更改角色后等待)

    moveTo(*monitor_settings.登录坐标)
    time.sleep(0.3)
    leftClick()
    time.sleep(monitor_settings.登录后等待)

    logger.info("已重置副本进度，等待重新加载...")


def self_kill():
    """用火箭筒自灭"""
    press(base_settings.重武器按键)
    time.sleep(1.5)
    move(0, get_resize(1080), relative=True)
    time.sleep(0.5)
    leftClick()


# ============================================================
# 收集 & 其他
# ============================================================

def change_window():
    """Alt+Tab 切换窗口"""
    keyDown("alt")
    time.sleep(0.1)
    keyDown("tab")
    time.sleep(0.1)
    keyUp("tab")
    keyUp("alt")


def open_dim_and_collect():
    """切换到 DIM / Ishtar 收集装备"""
    change_window()
    time.sleep(0.5)
    moveTo(*get_resize(600, 980))
    time.sleep(0.3)
    leftClick()
    time.sleep(0.5)
    keyDown("r")
    time.sleep(10)
    moveTo(*get_resize(1910, 960))
    time.sleep(0.3)
    leftClick()
    time.sleep(0.5)
    moveTo(*get_resize(1200, 980))
    time.sleep(0.3)
    leftClick()
    time.sleep(0.5)
    keyDown("ctrl")
    time.sleep(0.1)
    keyDown("v")
    time.sleep(0.1)
    keyUp("v")
    keyUp("ctrl")
    time.sleep(0.5)
    press("enter")
    time.sleep(0.5)
    change_window()
    time.sleep(0.5)
