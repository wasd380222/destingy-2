import dataclasses
import tomllib
from pathlib import Path

from size import MONITOR_HEIGHT
import size as size_module
from loguru import logger

SETTINGS_PATH = Path("./settings.toml")


@dataclasses.dataclass
class BaseSettings:
    log_level: str
    debug: bool
    collect: bool

    # 按键绑定
    飞升按键: str
    超能按键: str
    近战按键: str
    手雷按键: str
    终结技按键: str
    主武器按键: str
    副武器按键: str
    重武器按键: str
    插旗按键: str

    resolution: str = ""


@dataclasses.dataclass
class Config:
    """分辨率相关参数 — 基于 888888888888888888888888888.rec 录制校准 (近战版)"""

    # ===== 阶段1: 飞升 =====
    飞升后等待: float                    # X→S后退间隔(s), 录制: 1.578s

    # ===== 阶段2: 两次瞄准 (仅此两处有鼠标移动) =====
    第一次ADS偏移: tuple                 # ① C近战前瞄准(px), 录制: (-1512, 33)
    近战前等待: float                    # ADS瞄准后→C近战前额外等待(s), 等怪出现
    第一次ADS后等待: float               # 近战释放→超能前瞄准间隔(s)
    超能前瞄准偏移: tuple                # ② F超能前瞄准(px), 录制: (265, 23)
    超能后等待: float                    # F→冲刺间隔(s), 录制: 1.687s

    # ===== 阶段2: 飞升后战斗 - 冲刺+终结 =====
    冲刺A时间: float                     # 冲刺前A侧移持续时间(s), 录制: 0.125s
    冲刺瞄准偏移: tuple                  # 冲刺中鼠标微调(px), 默认: (0, 0)
    冲刺到终结时间: float                # 冲刺→G终结间隔(s), 录制: 0.156s
    终结后等待: float                    # G后等待(s)

    # ===== 全局 =====
    团灭后等待时间: float
    等待Boss死亡最长时间: float
    等待Boss死亡: float
    跑离Boss时间: float
    打开菜单后等待: float
    更改角色后等待: float
    登录后等待: float
    更改角色坐标: tuple
    登录坐标: tuple
    重置进度前进时间: float
    重开后等待时间: float


settings = tomllib.loads(SETTINGS_PATH.read_text("utf-8"))
base_settings = BaseSettings(**settings.pop("base"))

# 如果配置了强制分辨率，覆盖自动检测
if base_settings.resolution:
    size_module.force_resolution(base_settings.resolution)
    MONITOR_HEIGHT = size_module.MONITOR_HEIGHT

monitor_settings = Config(**settings.pop(f"{MONITOR_HEIGHT}p"))
logger.info(f"使用 {MONITOR_HEIGHT}p 配置")
