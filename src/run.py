"""
run.py — 棱镜虚空猎踢Boss主循环

完整流程:
  飞升前严格回放录制(20.4s) → X飞升 → 飞升后战斗序列 → 检测 → 重开

热键: F8=启动  F10=终止
      F2/F3=粗调  F5/F6=精调  F7=下一个  F1=上一个  F4=显示全部
终端: 回车=启动  q+回车=退出
"""

import time
import sys
import msvcrt
from pathlib import Path
from loguru import logger

from overlay import overlay


# ============================================================
# 全局状态
# ============================================================
running = False
exiting = False


def start_running():
    global running
    if not running:
        running = True
        overlay.update(running=True, phase="启动中...")
        logger.success(">>> 脚本启动! (F10=终止)")
    else:
        logger.info(">>> 已在运行中")


def stop_script():
    global exiting, running
    exiting = True
    running = False
    overlay.update(running=False, phase="已停止")
    try:
        from directx import set_abort
        set_abort(True)
    except Exception:
        pass
    logger.info(">>> 正在终止...")


def setup_hotkeys():
    try:
        import keyboard
        keyboard.add_hotkey("f8", start_running)
        keyboard.add_hotkey("f10", stop_script)

        from tuner import decrease, increase, coarse_decrease, coarse_increase, cycle_next, cycle_prev, show_all
        keyboard.add_hotkey("f5", decrease)
        keyboard.add_hotkey("f6", increase)
        keyboard.add_hotkey("f2", coarse_decrease)
        keyboard.add_hotkey("f3", coarse_increase)
        keyboard.add_hotkey("f7", cycle_next)
        keyboard.add_hotkey("f1", cycle_prev)
        keyboard.add_hotkey("f4", show_all)

        logger.info("热键: F8=启动  F10=终止  F2/F3=粗调  F5/F6=精调  F7=下个  F1=上个  F4=列表")
        return True
    except Exception as e:
        logger.info(f"全局热键不可用 ({e})，使用终端控制")
        return False


def check_terminal_input():
    if not msvcrt.kbhit():
        return
    ch = msvcrt.getch()
    if ch == b'\r':
        start_running()
    elif ch in (b'q', b'Q'):
        while msvcrt.kbhit():
            extra = msvcrt.getch()
            if extra == b'\r':
                break
        stop_script()
    elif ch == b'\x03':
        stop_script()


# ============================================================
# 主循环
# ============================================================

BOSS_HP_CHECK_INTERVAL = 1.0
RESPAWN_WAIT_BONUS = 5.0


def run():
    global running

    from directx import (
        pre_ascension_sequence,
        set_abort,
        use_ascension,
        post_ascension_combat,
        self_kill,
        open_dim_and_collect,
        sprint_forward,
        release_all_movement_keys,
        AbortError,
    )
    from settings import base_settings, monitor_settings

    # 初始化微调系统
    from tuner import init as tuner_init
    tuner_init(monitor_settings, "./settings.toml")

    logger.add("./logs/d2-ogre-kick_{time}.log", level="INFO", rotation="10 MB")
    logger.info("=" * 50)
    logger.info("D2 Ogre Kick - 棱镜虚空猎踢Boss v3 (近战版)")
    logger.info("流程: 录制回放(18s)→飞升→战斗序列(ADS+近战→F超能→冲刺+G终结)")
    logger.info("=" * 50)

    has_hotkey = setup_hotkeys()
    if has_hotkey:
        logger.info("按 F8 启动，F10 随时终止...")
    else:
        logger.info("按 回车 启动... (q+回车=退出)")
    logger.info("=" * 50)

    # 启动悬浮状态框
    overlay.start()
    overlay.update(phase="等待F8启动", running=False)

    if base_settings.debug:
        Path("./debug").mkdir(exist_ok=True)

    time.sleep(2)

    total_rounds = 0
    success_count = 0
    consecutive_fails = 0
    is_collected = 0
    last_heartbeat = time.time()

    # 准备开始（假设已经在旗点）
    logger.info("准备开始，请确保已站在旗点...")
    time.sleep(3)

    # ============================================================
    # 主循环
    # ============================================================
    while not exiting:

        check_terminal_input()

        if not running:
            time.sleep(0.3)
            # 心跳: 每 5 秒刷新 status.json, 防止 overlay_main 误判退出
            now = time.time()
            if now - last_heartbeat > 5:
                overlay.update()
                last_heartbeat = now
            continue

        # 连续失败过多 → 自尽重生
        if consecutive_fails >= 10:
            logger.warning(f"连续 {consecutive_fails} 次失败，自尽重生...")
            overlay.update(phase="自尽重生中...")
            self_kill()
            time.sleep(monitor_settings.团灭后等待时间)
            consecutive_fails = 0
            continue

        # 每5轮收件
        if success_count > 0 and success_count % 5 == 0 and is_collected == 0 and base_settings.collect:
            logger.info("收件...")
            overlay.update(phase="收件中...")
            open_dim_and_collect()
            is_collected = 1

        # 新一轮
        total_rounds += 1
        rate = 0 if total_rounds == 0 else success_count / total_rounds
        logger.info(f"[第 {total_rounds} 轮] OK:{success_count} NG:{consecutive_fails} {rate:.1%}")
        overlay.update(rounds=total_rounds, success=success_count, phase="飞升前序列")

        try:
            # ==================== 完整流程 ====================
            pre_ascension_sequence()     # 1. W→A→E插旗→E吃旗→2→冲刺→D/A走位→SPACE跳
            use_ascension()             # 2. X飞升→等待动画
            post_ascension_combat()     # 3. S后退→ADS+近战→F超能→冲刺+G终结

            # 终结技完成，停止等待手动调参
            logger.success(f"第 {total_rounds} 轮执行完毕，按 F8 重新开始")
            overlay.update(phase="完成, 等待F8", running=False)
            running = False

        except AbortError:
            logger.info("用户中止序列，清理按键...")
            release_all_movement_keys()
            overlay.update(phase="已中止", running=False)
            consecutive_fails = 0
            continue

        except Exception as e:
            if exiting:
                logger.info("用户中止")
                break
            logger.error(f"操作异常: {e}")
            overlay.update(phase=f"异常: {e}")
            consecutive_fails += 1
            self_kill()
            continue

    logger.info("脚本退出")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Ctrl+C 停止")
    except Exception as e:
        logger.exception(e)
    finally:
        overlay.stop()
