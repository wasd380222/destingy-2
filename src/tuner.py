"""
tuner.py — 运行时参数微调系统

热键:
  F5: 减少当前参数（精调）
  F6: 增加当前参数（精调）
  F2: 减少当前参数（粗调, 5x步长）
  F3: 增加当前参数（粗调, 5x步长）
  F7: 下一个参数
  F1: 上一个参数
  F4: 显示所有参数

所有调整立即生效并自动保存到 settings.toml
"""

import re
from pathlib import Path
from loguru import logger

# ============================================================
# 可调参数定义
# ============================================================

TUNE_PARAMS = [
    # (显示名, 属性名, 元组索引或None, 步长, 说明)
    # --- 两次瞄准 (仅此两处有鼠标移动) ---
    ("①一次ADS偏移X",   "第一次ADS偏移",     0,    10,    "C近战前水平瞄准(px)"),
    ("①一次ADS偏移Y",   "第一次ADS偏移",     1,    5,     "C近战前垂直瞄准(px)"),
    ("近战前等待",       "近战前等待",        None, 0.05,  "ADS瞄准后→C近战前额外等待(s)"),
    ("②超能前瞄准X",    "超能前瞄准偏移",    0,    5,     "F超能前水平瞄准(px)"),
    ("②超能前瞄准Y",    "超能前瞄准偏移",    1,    3,     "F超能前垂直瞄准(px)"),
    # --- 时序 ---
    ("飞升后等待",       "飞升后等待",        None, 0.05,  "X飞升→S后退间隔(s)"),
    ("一次ADS后等待",    "第一次ADS后等待",   None, 0.05,  "近战释放→超能前瞄准间隔(s)"),
    ("超能后等待",       "超能后等待",        None, 0.05,  "F超能→冲刺间隔(s)"),
    ("冲刺A时间",        "冲刺A时间",         None, 0.01,  "冲刺前A侧移持续时间(s)"),
    ("冲刺瞄准X",        "冲刺瞄准偏移",      0,    5,     "冲刺中水平微调(px)"),
    ("冲刺瞄准Y",        "冲刺瞄准偏移",      1,    3,     "冲刺中垂直微调(px)"),
    ("冲刺到终结",       "冲刺到终结时间",    None, 0.02,  "冲刺→G终结间隔(s)"),
    ("终结后等待",       "终结后等待",        None, 0.1,   "G终结后等待(s)"),
    # --- 全局 ---
    ("等待Boss死亡",     "等待Boss死亡",      None, 0.5,   "等Boss被踢飞(s)"),
    ("跑离Boss时间",     "跑离Boss时间",      None, 0.5,   "跑离场地时长(s)"),
    ("团灭后等待",       "团灭后等待时间",    None, 0.5,   "团灭后等待(s)"),
]

# ============================================================
# 内部状态
# ============================================================

_current_idx = 0
_monitor_settings = None
_settings_path = None
_section = None


def _get_val(p):
    """获取参数当前值"""
    name, attr, idx, step, desc = p
    val = getattr(_monitor_settings, attr)
    if idx is not None:
        return val[idx]
    return val


def _set_val(p, new_val):
    """设置参数值（内存 + 持久化）"""
    name, attr, idx, step, desc = p
    if idx is not None:
        old = list(getattr(_monitor_settings, attr))
        old[idx] = new_val
        object.__setattr__(_monitor_settings, attr, tuple(old))
    else:
        object.__setattr__(_monitor_settings, attr, new_val)

    _save_to_toml(attr, idx, new_val)


def _save_to_toml(attr, idx, new_val):
    """写入 settings.toml — 按 section 定位，逐行替换"""
    try:
        content = _settings_path.read_text("utf-8")
        lines = content.split("\n")
        result = []
        in_section = False
        replaced = False

        for line in lines:
            stripped = line.strip()
            # 检测 section 头
            if stripped.startswith("[") and stripped.endswith("]"):
                in_section = (stripped == f"[{_section}]")
                result.append(line)
                continue

            # 只在目标 section 内替换
            if not in_section or replaced:
                result.append(line)
                continue

            # 检查当前行是否是目标参数
            if f'"{attr}"' in stripped and "=" in stripped:
                if idx is not None:
                    # 数组值: "key" = [a, b] → 替换对应索引
                    m = re.match(r'^(\s*".*?"\s*=\s*\[)(.*?)(\])', line)
                    if m:
                        vals = [v.strip() for v in m.group(2).split(",")]
                        if idx < len(vals):
                            vals[idx] = str(new_val)
                        result.append(m.group(1) + ", ".join(vals) + m.group(3))
                        replaced = True
                        continue
                else:
                    # 标量值: "key" = 1.23 → 替换值部分
                    m = re.match(r'^(\s*".*?"\s*=\s*)(-?[\d.]+)(.*)', line)
                    if m:
                        result.append(m.group(1) + str(new_val) + m.group(3))
                        replaced = True
                        continue

            result.append(line)

        if replaced:
            _settings_path.write_text("\n".join(result), "utf-8")
            logger.debug(f"💾 已保存 [{_section}] {attr} = {new_val}")
        else:
            logger.warning(f"⚠ 未在 [{_section}] 找到参数 {attr}，尝试全局查找...")
            # 回退：全局查找替换（不限制 section）
            _save_global(attr, idx, new_val)

    except Exception as e:
        logger.warning(f"保存 settings.toml 失败: {e}")


def _save_global(attr, idx, new_val):
    """回退方案：全局替换"""
    content = _settings_path.read_text("utf-8")
    if idx is not None:
        pat = rf'("{re.escape(attr)}"\s*=\s*\[)([^\]]*?)(\])'
        def _repl(m):
            vals = [v.strip() for v in m.group(2).split(",")]
            if idx < len(vals):
                vals[idx] = str(new_val)
            return m.group(1) + ", ".join(vals) + m.group(3)
        content = re.sub(pat, _repl, content, count=1)
    else:
        pat = rf'("{re.escape(attr)}"\s*=\s*)(-?[\d.]+)'
        content = re.sub(pat, rf'\g<1>{new_val}', content, count=1)
    _settings_path.write_text(content, "utf-8")


def _show_current():
    p = TUNE_PARAMS[_current_idx]
    name, attr, idx, step, desc = p
    val = _get_val(p)
    logger.info(f"🎯 [{name}] = {val} | {desc} | F5/F6 ±{step}")


# ============================================================
# 公开 API
# ============================================================

def init(monitor_settings, toml_path: str):
    """初始化微调器，传入 monitor_settings 和 settings.toml 路径"""
    global _monitor_settings, _settings_path, _section
    _monitor_settings = monitor_settings
    _settings_path = Path(toml_path)

    # 推断当前使用的分辨率 section
    import tomllib
    raw = tomllib.loads(_settings_path.read_text("utf-8"))
    for key in raw:
        if key.endswith("p") and key != "base" and "resolution" not in str(raw[key]):
            pass
    # 从 settings 重新读一次拿到 section
    from settings import MONITOR_HEIGHT
    _section = f"{MONITOR_HEIGHT}p"

    logger.info(f"🎛️ 微调系统就绪 ({len(TUNE_PARAMS)} 个参数, 当前分辨率: {_section})")
    _show_current()


def cycle_next():
    global _current_idx
    _current_idx = (_current_idx + 1) % len(TUNE_PARAMS)
    _show_current()


def cycle_prev():
    global _current_idx
    _current_idx = (_current_idx - 1) % len(TUNE_PARAMS)
    _show_current()


def increase():
    p = TUNE_PARAMS[_current_idx]
    old = _get_val(p)
    new = round(old + p[3], 3) if isinstance(old, float) else old + p[3]
    _set_val(p, new)
    logger.success(f"  ✅ [{p[0]}]: {old} → {new}")


def decrease():
    p = TUNE_PARAMS[_current_idx]
    old = _get_val(p)
    if isinstance(old, float):
        new = round(max(0, old - p[3]), 3)
    else:
        new = old - p[3]
    _set_val(p, new)
    logger.success(f"  ✅ [{p[0]}]: {old} → {new}")


def coarse_increase():
    """粗调增大: 5x 步长"""
    p = TUNE_PARAMS[_current_idx]
    old = _get_val(p)
    big_step = p[3] * 5
    new = round(old + big_step, 3) if isinstance(old, float) else old + big_step
    _set_val(p, new)
    logger.success(f"  🔼 粗调 [{p[0]}]: {old} → {new}  (+{big_step})")


def coarse_decrease():
    """粗调减小: 5x 步长"""
    p = TUNE_PARAMS[_current_idx]
    old = _get_val(p)
    big_step = p[3] * 5
    if isinstance(old, float):
        new = round(max(0, old - big_step), 3)
    else:
        new = old - big_step
    _set_val(p, new)
    logger.success(f"  🔽 粗调 [{p[0]}]: {old} → {new}  (-{big_step})")


def show_all():
    logger.info("=" * 50)
    logger.info("📋 当前所有可调参数:")
    for i, p in enumerate(TUNE_PARAMS):
        marker = "➤" if i == _current_idx else " "
        val = _get_val(p)
        logger.info(f" {marker} [{p[0]:10s}] = {str(val):>8s}   ({p[4]})")
    logger.info("=" * 50)
    logger.info("F2/F3=粗调  F5/F6=精调  F7=下一个  F4=显示全部")
