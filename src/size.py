from loguru import logger
from PIL import ImageGrab

# 自动检测分辨率
_detected_width, _detected_height = ImageGrab.grab().size
logger.info(f"屏幕分辨率: {_detected_width}x{_detected_height}")

MONITOR_WIDTH = _detected_width
MONITOR_HEIGHT = _detected_height


def force_resolution(res: str):
    """强制覆盖分辨率（用于显示器≠游戏分辨率的情况）"""
    global MONITOR_WIDTH, MONITOR_HEIGHT, RESIZE_RATIO
    if res == "1080p":
        MONITOR_WIDTH, MONITOR_HEIGHT = 1920, 1080
        logger.info(f"已强制分辨率: 1920x1080")
    elif res == "1440p":
        MONITOR_WIDTH, MONITOR_HEIGHT = 2560, 1440
        logger.info(f"已强制分辨率: 2560x1440")
    else:
        logger.warning(f"未知分辨率 {res}，使用自动检测")
    _recompute()


RESIZE_RATIO = MONITOR_WIDTH / 2560
resize = lambda x: int(x * RESIZE_RATIO)


def get_resize(*x: int):
    if len(x) == 1:
        return resize(x[0])
    return tuple(map(resize, x))


# ============================================================
# 检测区域 — 用于视觉状态检测
# 坐标以 2560x1440 为基准，通过 get_resize 自动缩放
# ============================================================

def _recompute():
    """重新计算所有坐标（在 force_resolution 后调用）"""
    global RESIZE_RATIO, BOSS_HP_BAR_POSITION, BOSS_HP_BAR_WIDTH, BOSS_HP_BAR_HEIGHT
    global PLAYER_HP_BAR_POSITION, PLAYER_HP_BAR_WIDTH, PLAYER_HP_BAR_HEIGHT
    global SUPER_BAR_POSITION, SUPER_BAR_WIDTH, SUPER_BAR_HEIGHT
    global BOSS_HP_BAR_BBOX, PLAYER_HP_BAR_BBOX, SUPER_BAR_BBOX

    RESIZE_RATIO = MONITOR_WIDTH / 2560

    BOSS_HP_BAR_POSITION = get_resize(1100, 1290)
    BOSS_HP_BAR_WIDTH, BOSS_HP_BAR_HEIGHT = get_resize(350, 15)

    PLAYER_HP_BAR_POSITION = get_resize(880, 130)
    PLAYER_HP_BAR_WIDTH, PLAYER_HP_BAR_HEIGHT = get_resize(350, 15)

    SUPER_BAR_POSITION = get_resize(50, 1015)
    SUPER_BAR_WIDTH, SUPER_BAR_HEIGHT = get_resize(250, 12)

    BOSS_HP_BAR_BBOX = (
        *BOSS_HP_BAR_POSITION,
        BOSS_HP_BAR_POSITION[0] + BOSS_HP_BAR_WIDTH,
        BOSS_HP_BAR_POSITION[1] + BOSS_HP_BAR_HEIGHT,
    )
    PLAYER_HP_BAR_BBOX = (
        *PLAYER_HP_BAR_POSITION,
        PLAYER_HP_BAR_POSITION[0] + PLAYER_HP_BAR_WIDTH,
        PLAYER_HP_BAR_POSITION[1] + PLAYER_HP_BAR_HEIGHT,
    )
    SUPER_BAR_BBOX = (
        *SUPER_BAR_POSITION,
        SUPER_BAR_POSITION[0] + SUPER_BAR_WIDTH,
        SUPER_BAR_POSITION[1] + SUPER_BAR_HEIGHT,
    )


# 初始计算
BOSS_HP_BAR_POSITION = get_resize(1100, 1290)
BOSS_HP_BAR_WIDTH, BOSS_HP_BAR_HEIGHT = get_resize(350, 15)

PLAYER_HP_BAR_POSITION = get_resize(880, 130)
PLAYER_HP_BAR_WIDTH, PLAYER_HP_BAR_HEIGHT = get_resize(350, 15)

SUPER_BAR_POSITION = get_resize(50, 1015)
SUPER_BAR_WIDTH, SUPER_BAR_HEIGHT = get_resize(250, 12)

BOSS_HP_BAR_BBOX = (
    *BOSS_HP_BAR_POSITION,
    BOSS_HP_BAR_POSITION[0] + BOSS_HP_BAR_WIDTH,
    BOSS_HP_BAR_POSITION[1] + BOSS_HP_BAR_HEIGHT,
)
PLAYER_HP_BAR_BBOX = (
    *PLAYER_HP_BAR_POSITION,
    PLAYER_HP_BAR_POSITION[0] + PLAYER_HP_BAR_WIDTH,
    PLAYER_HP_BAR_POSITION[1] + PLAYER_HP_BAR_HEIGHT,
)
SUPER_BAR_BBOX = (
    *SUPER_BAR_POSITION,
    SUPER_BAR_POSITION[0] + SUPER_BAR_WIDTH,
    SUPER_BAR_POSITION[1] + SUPER_BAR_HEIGHT,
)
