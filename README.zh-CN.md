# 美签预约监控工具

📖 [English](./README.md)

自动监控 [usvisascheduling.com](https://www.usvisascheduling.com) 上的美国签证可预约日期，支持邮件提醒和自动预定。

## 功能

- 实时监控签证预约日期变动
- 支持多个领事馆：上海、武汉、沈阳
- 随机化检查间隔（3–9 分钟），降低被检测风险
- 日期变动时自动发送邮件通知（新增 / 移除）
- 可配置日期范围的自动预定（含安全模式 Dry Run）
- 终端内可视化倒计时
- 使用 `undetected_chromedriver` 规避反爬检测
- 支持手动登录以处理验证码 / 二次验证

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/CChen19/us-visa-scheduler.git
cd us-visa-scheduler
pip install -r requirements.txt
```

### 2. 配置

打开 `main.py`，编辑顶部的配置区域：

**领事馆选择**

```python
LOCATION_NAME = "SHANGHAI"  # "SHANGHAI" / "WUHAN" / "SHENYANG"
```

**邮件配置** — 需要使用 SMTP 授权码（如 QQ 邮箱授权码）

```python
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
EMAIL_SENDER = "your_email@qq.com"
EMAIL_PASSWORD = "your_smtp_app_password"
EMAIL_RECEIVER = "your_receiver@example.com"
```

**自动预定**（可选）

```python
BOOKING_CONFIG = {
    "BOOKING_ENABLED": False,
    "EARLIEST_DATE_STR": "2025-08-01",
    "LATEST_DATE_STR": "2025-08-31",
    "DRY_RUN": True,              # True = 仅模拟，False = 真正提交
    "KEEP_BROWSER_OPEN_ON_EXIT": True
}
```

**申请人姓名** — 在 `main.py` 中搜索 `Your Name`，替换为你在预约页面上显示的姓名。

### 3. 运行

```bash
python main.py
```

浏览器会自动打开，请手动完成登录和验证码，然后在终端按 **Enter** 键。脚本会接管后续操作。

> 提示：可以使用 `tmux` 或 `screen` 在远程服务器上保持运行。

## 工作原理

1. 打开预约网站，你手动完成登录。
2. 进入监控循环：刷新页面 → 选择目标领事馆 → 读取日历上的可用日期。
3. 与上一次快照对比，有变动则发送邮件。
4. 如果开启了自动预定，且发现符合日期范围的时间段，会自动走完预定流程。
5. 等待随机间隔后重复。

## 邮件示例

```
Subject: 【签证监控】SHANGHAI F1签证日期变动！

领事馆: SHANGHAI

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
- 登录状态过期后可能需要重新手动登录。
- 请保持网络稳定以避免中断。

## 致谢

本项目基于 [SYuan03](https://github.com/SYuan03/VisaAppointmentWatcher) 的原始工作进行改进。感谢原作者的优秀贡献！

## License

[MIT](./LICENSE)
