"""
overlay_main.py — 悬浮框独立进程入口

由 start.bat 启动, 与 run.py 进程分离。
读取 ./logs/overlay_status.json 渲染左上角小绿框。

退出条件:
  - run.py 正常退出 → status.json 中 exit=true → 本进程关闭
  - run.py 崩溃 → status.json 超过 15 秒未更新 → 本进程自动退出
  - 手动关闭窗口
"""

from overlay import OverlayWindow


if __name__ == "__main__":
    OverlayWindow().run()
