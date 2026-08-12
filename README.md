# d2-ogre-kick

基于溜溜球99九九的 [B站视频 BV1x5Ki6cE8r](https://www.bilibili.com/video/BV1x5Ki6cE8r) 手法实现的棱镜虚空猎自动踢Boss脚本。

> 战争领主的废墟首Boss（拉希尔 / Rathil）自动化踢杀，使用虚空超能聚怪 + 无礼言论终结的套路。

## 原理

| 阶段 | 操作 | 说明 |
|------|------|------|
| 1 | 开怪 | 接近Boss开枪触发 |
| 2 | 飞升分身 | Ascension 留下克隆体吸引Boss仇恨 |
| 3 | 清右侧小怪 | 火箭筒清掉右边干扰小怪 |
| 4 | 虚空超能 | Shadowshot: Deadfall 射箭聚怪 |
| 5 | 无礼言论一枪 | 对被拉过来的小怪开一枪 → 终结血量 |
| 6 | 冲刺终结 | 三点一线直冲，终结踢Boss |

## 环境

- Python 3.11 ~ 3.12
- Windows 10/11
- 屏幕分辨率 1920×1080 或 2560×1440

## 安装

```bash
pip install -r requirements.txt
```

## 配置

编辑 `settings.toml`：

1. **按键绑定** — 按你在游戏里的设置修改 `[base]` 中的按键
2. **1080p / 1440p 参数** — 如果坐标不准，开启 `debug = true` 查看截图并微调

## 运行

```bash
cd d2-ogre-kick
python src/run.py
```

按 `Ctrl+C` 停止。

## 调试

在 `settings.toml` 中设置 `debug = true`，脚本会在 `./debug/` 目录保存每次检测的截图，方便校准参数。

## 注意事项

- 需要配装棱镜虚空猎 + 飞升星相 + 无礼言论 (Indebted Kindness) + 火箭筒
- Boss 两腿之间射箭 → 小怪聚拢 → 一枪进终结 → 直冲终结
- 冲之前不要下台阶，否则 Boss 会提前抬脚
- 首次运行会先重置一次进度，确保在正确的出生点
