import cv2
import numpy as np
from functools import wraps
from PIL import ImageGrab, Image

from size import (
    MONITOR_WIDTH,
    BOSS_HP_BAR_BBOX,
    PLAYER_HP_BAR_BBOX,
    SUPER_BAR_BBOX,
)


# ============================================================
# 装饰器 — 调试 & 性能
# ============================================================

def image_log(func: callable):
    """调试模式下保存截图"""
    from datetime import datetime
    from settings import base_settings

    @wraps(func)
    def inner():
        image = func()
        if base_settings.debug:
            time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
            file_name = f"{func.__name__}_{time_str}.png"
            image.save(f"./debug/{file_name}")
        return image

    return inner


def timer_log(func: callable):
    """记录函数耗时"""
    @wraps(func)
    def inner(*args, **kwargs):
        import time
        start_time = time.monotonic()
        result = func(*args, **kwargs)
        return result

    return inner


def result_log(func: callable):
    """记录返回结果"""
    from loguru import logger

    @wraps(func)
    def inner(*args, **kwargs):
        result = func(*args, **kwargs)
        logger.debug(f"[{func.__name__}] 结果: {result:.3f}")
        return result

    return inner


# ============================================================
# 截图函数
# ============================================================

@image_log
@timer_log
def get_boss_hp_bar_image():
    return ImageGrab.grab(bbox=BOSS_HP_BAR_BBOX)


@image_log
@timer_log
def get_player_hp_bar_image():
    return ImageGrab.grab(bbox=PLAYER_HP_BAR_BBOX)


@image_log
@timer_log
def get_super_bar_image():
    return ImageGrab.grab(bbox=SUPER_BAR_BBOX)


# ============================================================
# 图像处理工具
# ============================================================

def conver_image_to_open_cv(image: Image.Image):
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def get_mask_ratio(image: np.ndarray, lower_bound: np.ndarray, upper_bound: np.ndarray):
    """计算指定颜色范围的像素占比"""
    mask = cv2.inRange(image, lower_bound, upper_bound)
    return np.sum(mask == 255) / (image.size / 3)


# ============================================================
# 颜色范围定义
# （RGB 格式，内部自动翻转为 BGR 给 OpenCV 使用）
# ============================================================

# Boss 血条 — 橙色/红棕色
BOSS_HP_COLOR_RANGE = (
    np.array([180, 60, 0][::-1]),
    np.array([255, 140, 50][::-1]),
)

# 超能条满 — 亮黄色/金色
SUPER_FULL_COLOR_RANGE = (
    np.array([200, 180, 0][::-1]),
    np.array([255, 255, 80][::-1]),
)

# 玩家血条 — 白色/浅灰（表示存活）
PLAYER_HP_COLOR_RANGE = (
    np.array([180, 180, 180][::-1]),
    np.array([255, 255, 255][::-1]),
)


# ============================================================
# 检测函数
# ============================================================

@result_log
@timer_log
def get_boss_hp_bar_mask_ratio():
    """检测 Boss 血条是否存在。> 0.1 表示 Boss 存活"""
    return get_mask_ratio(
        conver_image_to_open_cv(get_boss_hp_bar_image()),
        *BOSS_HP_COLOR_RANGE,
    )


@result_log
@timer_log
def get_player_hp_bar_mask_ratio():
    """检测玩家血条是否存在。> 0.3 表示玩家存活"""
    return get_mask_ratio(
        conver_image_to_open_cv(get_player_hp_bar_image()),
        *PLAYER_HP_COLOR_RANGE,
    )


@result_log
@timer_log
def get_super_full_mask_ratio():
    """检测超能条是否充满。> 0.5 表示超能已满"""
    return get_mask_ratio(
        conver_image_to_open_cv(get_super_bar_image()),
        *SUPER_FULL_COLOR_RANGE,
    )


def is_boss_alive():
    """Boss 存活判断"""
    return get_boss_hp_bar_mask_ratio() > 0.1


def is_player_alive():
    """玩家存活判断"""
    return get_player_hp_bar_mask_ratio() > 0.3


def is_super_ready():
    """超能就绪判断"""
    return get_super_full_mask_ratio() > 0.5
