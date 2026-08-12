"""
overlay_main.py — 悬浮框独立进程入口

由 start.bat 启动, 与 run.py 进程分离。
读取 ./logs/overlay_status.json 渲染左上角小绿框。

退出条件:
  - run.py 正常退出 → status.json 中 exit=true → 本进程关闭
  - run.py 崩溃 → status.json 超过 15 秒未更新 → 本进程自动退出
  - 手动关闭窗口

所有未捕获异常写入 ./logs/overlay_error.log
"""

import sys
import traceback
from pathlib import Path

# 确保 src 目录在 sys.path 中
src_dir = str(Path(__file__).parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from overlay import OverlayWindow, _log_error


if __name__ == "__main__":
    try:
        OverlayWindow().run()
    except Exception as e:
        _log_error(f"overlay_main 顶层异常: {e}\n{traceback.format_exc()}")
        # 重新抛出让 start.bat 能看到退出码
        raise
