# 美签预约监控工具

📖 [English](./README.md)

自动监控 [usvisascheduling.com](https://www.usvisascheduling.com) 上的美国签证可预约日期，支持邮件提醒和自动预定。

登录步骤需要手动完成验证码，因此脚本需要一个可见的浏览器界面。请在有显示器的本地机器上运行：Windows 的 WSL2、树莓派，或任意带显示输出的 Ubuntu 系统。

## 前提条件

- WSL2（Windows 11 with WSLg）、Raspberry Pi OS，或 Ubuntu 22.04+
- 已安装 Git

## 第一步 — 克隆仓库并初始化

```bash
git clone https://github.com/elvinzhou/us-visa-scheduler.git
cd us-visa-scheduler
chmod +x setup.sh && ./setup.sh
```

脚本将自动安装以下内容：
- Google Chrome（x86-64）或 Chromium（ARM / 树莓派）
- Python 虚拟环境及所有依赖
- tmux

> **WSL 说明：** 浏览器窗口需要 WSLg（Windows 11 版本 22000 及以上）才能正常显示。如果使用 Windows 10 WSL2，请先安装 X 服务端（如 [VcXsrv](https://sourceforge.net/projects/vcxsrv/)），然后在运行脚本前执行 `export DISPLAY=:0`。

## 第二步 — 配置

将 `.env.example` 复制为 `.env` 并填写你的信息：

```bash
cp .env.example .env
nano .env
```

```dotenv
# 申请人姓名（必须与预约页面上显示的完全一致）
APPLICANT_NAME=你的姓名

# 邮件通知 — 支持多个收件人，用逗号分隔
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_smtp_app_password
EMAIL_RECEIVER=receiver1@example.com,receiver2@example.com

# 可选 — 以下为默认值
# SMTP_SERVER=smtp.qq.com
# SMTP_PORT=465

# 监控的领事馆：SHANGHAI / WUHAN / SHENYANG（默认：SHENYANG）
# LOCATION_NAME=SHENYANG

# 自动预定设置（均为可选，以下为默认值）
# BOOKING_ENABLED=false         # 设为 "true" 以启用自动预定
# EARLIEST_DATE_STR=2025-08-01  # 可接受的最早预约日期
# LATEST_DATE_STR=2025-08-31    # 可接受的最晚预约日期
# DRY_RUN=true                  # "false" 表示真实提交；"true" 表示仅模拟
# KEEP_BROWSER_OPEN_ON_EXIT=true
```

## 第三步 — 运行监控脚本

```bash
tmux new -s visa
source .venv/bin/activate
python3 main.py
```

Chrome 窗口会在你的屏幕上打开，手动完成登录和验证码，然后在终端按 **Enter**。脚本将接管后续的循环监控。

使用 **Ctrl+B D** 分离 tmux——脚本在后台持续运行。之后如需重新查看：

```bash
tmux attach -t visa
```

## 工作原理

1. 打开预约网站，手动完成登录。
2. 进入监控循环：刷新页面 → 选择目标领事馆 → 读取日历上的可用日期。
3. 与上一次快照对比，有变动则发送邮件。
4. 如果开启了自动预定，且发现符合日期范围的时间段，会自动走完预定流程。
5. 等待随机间隔（通常 3–5 分钟，每隔若干次检查后进入 7–9 分钟的较长休眠）后重复。
6. 如果检测到会话过期（跳转至登录页），会提示重新登录，而不是静默重试。

## 邮件示例

```
Subject: 【签证监控】SHENYANG F1签证日期变动！

领事馆: SHENYANG

新增的可预约日期:
  ✅ 2025-08-15

不再可用的日期:
  ❌ 2025-08-10

当前所有可预约日期:
  - 2025-08-15
  - 2025-08-22
```

## 注意事项

- 仅供个人学习交流使用，请勿用于商业目的。
- 作者不对使用本工具产生的任何后果负责。
- 首次运行及会话过期后需手动重新登录。
- 请保持网络稳定以避免中断。

## 致谢

本项目基于 [SYuan03](https://github.com/SYuan03/VisaAppointmentWatcher) 的原始工作进行改进。

## License

[MIT](./LICENSE)
