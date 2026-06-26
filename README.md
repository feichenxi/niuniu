# NPoker（抢庄牛牛）- AI 扑克牌识别与辅助决策工具

基于 YOLO11 目标检测的「抢庄牛牛」扑克牌自动识别与辅助决策工具。通过截取安卓模拟器窗口屏幕，使用自训练 YOLO 模型识别牌面和按钮，**内置本地牛牛决策引擎**，无需服务器即可自动计算牌型和策略，也支持远程决策服务器。

## 功能特性

- **牌面识别**：使用 YOLO11 模型实时识别扑克牌花色和面值
- **按钮检测**：自动识别游戏界面中的倍率、退出、参场等按钮
- **多窗口并行**：支持同时处理 4 个模拟器窗口（2x2 布局）
- **本地决策引擎**：内置抢庄牛牛规则引擎，本地计算牌型和最优策略，微秒级响应
- **自动操作**：根据策略自动点击对应按钮（Win32 API / ADB）
- **性能分级**：3档显示模式适配不同主机性能

## 项目结构

```
QiangZhuangNiuNiu/
├── default.py          # 主程序入口
├── requirements.txt    # Python 依赖列表
├── core/
│   ├── __init__.py     # 包初始化
│   ├── click.py        # 窗口点击操作（Win32/ADB/PyAutoGUI）
│   ├── comm.py         # 通用工具（日志、数据库、UUID）
│   ├── config.py       # 全局状态配置
│   └── decision.py     # 本地决策引擎（牛牛牌型计算 & 策略）
├── model/
│   ├── card.pt         # 牌面检测模型（YOLO11）
│   ├── button.pt       # 按钮检测模型（YOLO11）
│   ├── dot.png         # 点击指示图标
│   └── text.ttf        # 中文字体文件
├── .gitignore
├── .env.example        # 环境配置模板
├── LICENSE             # MIT 许可证
└── README.md
```

## 环境要求

- **操作系统**：Windows 10/11
- **Python**：3.9+
- **GPU**：推荐 NVIDIA CUDA（CPU 也可运行，但速度较慢）
- **模拟器**：雷电模拟器 (dnplayer.exe)，4 个窗口标题分别为 w1、w2、w3、w4

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/feichenxi/niuniu.git
cd niuniu
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制配置模板
copy .env.example .env

# 编辑 .env 文件，填入你的服务器域名和数据库配置
```

> 注意：`model/card.pt` 和 `model/button.pt` 为自训练 YOLO 模型文件，已包含在仓库中。如需自行训练模型，请参考 [Ultralytics YOLO11 文档](https://docs.ultralytics.com/)。

### 4. 准备模拟器

- 启动 4 个雷电模拟器实例
- 确保窗口标题分别为 `w1`、`w2`、`w3`、`w4`
- 窗口应保持可见状态（不可最小化）

### 5. 运行程序

```bash
python default.py
```

运行后选择性能档位：
- `1`：全能主机 — 开启牌面显示 + 按钮小屏
- `2`：一般主机 — 仅开启牌面显示
- `3`：较差主机 — 仅核心功能

键盘控制：
- `↑` (Up) 键：启动自动化
- `↓` (Down) 键：停止自动化

## 决策原理

程序内置抢庄牛牛规则引擎，在本地完成所有计算，零配置、无需网络：

1. **牌型计算**：4 张牌中选 3 张，若和为 10 的倍数则有牛，剩余 1 张决定牛数
2. **4 窗口对比**：比较 4 个玩家的牌力，按排名分配策略
3. **策略输出**：好牌→高倍率抢庄，差牌→低倍率弃牌

数据示例（输入 → 输出）：
```
输入: 13.0,1.1,10.2,7.3|2.3,5.0,8.1,11.2|4.1,6.3,9.0,12.2|7.2,3.0,13.1,1.3
      ↑ w1 的 4 张牌        ↑ w2           ↑ w3           ↑ w4

输出:
  w1: {"text":"牛牛", "click":"yes", "color":"red",    "multiple":"5"}    ← 最强
  w2: {"text":"牛七", "click":"yes", "color":"yellow", "multiple":"2"}
  w3: {"text":"牛五", "click":"yes", "color":"green",  "multiple":"1"}
  w4: {"text":"无牛", "click":"no",  "color":"blue",   "multiple":""}     ← 最弱
```

## 技术架构

```
┌─────────────┐     截屏      ┌──────────────┐     识别      ┌─────────────┐
│ 雷电模拟器   │ ───────────→ │ Window Capture │ ───────────→ │ YOLO Model  │
│  (4 windows) │              │ (PrintWindow)  │              │ (card/btn)  │
└─────────────┘              └──────────────┘              └─────────────┘
                                                                  │
                                                                  │ 牌面数据
                                                                  ↓
                                                          ┌──────────────┐
                                                          │ 本地决策引擎  │
                                                          │ (牛牛计算+策略)│ ← 默认
                                                          └──────────────┘
                                                            │    ↑
                                                    无需联网 │    │ 可选配置
                                                            │  ┌──────────────┐
                                                            │  │ 远程决策服务器 │
                                                            │  └──────────────┘
                                                                  │
                                                                  │ 策略结果
                                                                  ↓
┌─────────────┐     点击      ┌──────────────┐
│ 雷电模拟器   │ ←────────── │ Click Module  │
│              │              │ (Win32/ADB)   │
└─────────────┘              └──────────────┘
```

## 注意事项

- 本项目仅适用于 Windows 平台（依赖 win32gui 等模块）
- YOLO 模型文件 (`card.pt`, `button.pt`) 约 150MB，请确保网络畅通
- 运行时需要模拟器窗口保持可见状态
- 建议使用 GPU 加速以获得更好的识别帧率

## 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交改动 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 联系方式

如有问题、建议或合作意向，欢迎通过以下方式联系我：

- **邮箱**：[44998076@qq.com](mailto:44998076@qq.com)
- **微信**：扫描下方二维码

![微信二维码](qrcode.png)

## 免责声明

本项目仅供学习和研究目的。请遵守当地法律法规，在合法合规的前提下使用。作者不对任何不当使用行为承担责任。
