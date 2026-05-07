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
- 自动检测会话过期并提示重新登录

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/elvinzhou/us-visa-scheduler.git
cd us-visa-scheduler
pip install -r requirements.txt
```

### 2. 配置

**领事馆选择** — 编辑 `main.py`：

```python
LOCATION_NAME = "SHANGHAI"  # "SHANGHAI" / "WUHAN" / "SHENYANG"
```

**自动预定** — 同样在 `main.py` 中（可选）：

```python
BOOKING_CONFIG = {
    "BOOKING_ENABLED": False,
    "EARLIEST_DATE_STR": "2025-08-01",
    "LATEST_DATE_STR": "2025-08-31",
    "DRY_RUN": True,              # True = 仅模拟，False = 真正提交
    "KEEP_BROWSER_OPEN_ON_EXIT": True
}
```

**环境变量** — 将 `.env.example` 复制为 `.env` 并填写你的信息：

```bash
cp .env.example .env
```

```dotenv
# 申请人姓名（必须与预约页面上显示的完全一致）
APPLICANT_NAME=你的姓名

# 邮件配置（使用 SMTP 授权码，如 QQ 邮箱授权码）
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_smtp_app_password
EMAIL_RECEIVER=your_receiver@example.com

# 可选 — 以下为默认值
# SMTP_SERVER=smtp.qq.com
# SMTP_PORT=465
```

`.env` 文件已被加入 `.gitignore`，不会被提交到代码仓库。

### 3. 运行

```bash
python main.py
```

浏览器会自动打开，请手动完成登录和验证码，然后在终端按 **Enter** 键。脚本会接管后续操作。

> 提示：可以使用 `tmux` 或 `screen` 在关闭终端后保持运行。

## 部署到 Oracle Cloud（免费，浏览器桌面）

登录步骤需要可视化浏览器来完成验证码。项目内附的 `setup.sh` 可在 Oracle Cloud **永久免费** 的 Ubuntu 22.04 虚拟机上自动搭建完整桌面环境，通过 noVNC 在浏览器中访问——无需安装任何 VNC 客户端。

### 1. 创建虚拟机

在 [cloud.oracle.com](https://cloud.oracle.com) 注册并创建免费虚拟机：
- **规格**：`VM.Standard.E2.1.Micro`（AMD x86，1 OCPU / 1 GB 内存）— 与 Chrome 兼容性最佳
- **镜像**：Ubuntu 22.04
- 创建时下载 SSH 密钥

### 2. 运行初始化脚本

打开 **Cloud Shell**（OCI 控制台顶部导航栏的 `>_` 图标），SSH 登录到虚拟机后执行：

```bash
git clone https://github.com/elvinzhou/us-visa-scheduler.git
cd us-visa-scheduler
chmod +x setup.sh && ./setup.sh
```

脚本会提示你设置 VNC 密码，然后自动安装并配置所有组件（桌面环境、noVNC、Chrome、Python 依赖、systemd 服务）。

### 3. 在 OCI 中开放 6080 端口

在 OCI 控制台中：
> 网络 → 虚拟云网络 → 你的 VCN → 安全列表 → 默认安全列表 → 添加入站规则
> - 源 CIDR：`0.0.0.0/0`（或填写你的 IP 以提高安全性）
> - 协议：TCP，端口：`6080`

### 4. 访问桌面

在浏览器中打开 `http://<虚拟机公网IP>:6080/vnc.html`，输入 VNC 密码，即可看到完整的 Xfce 桌面。

### 5. 运行监控脚本

在虚拟机桌面中打开终端：

```bash
cd us-visa-scheduler
cp .env.example .env   # 填写你的配置
tmux new -s visa
python3 main.py
```

在弹出的浏览器中完成验证码登录，按下 **Enter**，然后用 **Ctrl+B D** 分离 tmux 并关闭浏览器标签页。脚本将在后台持续运行，虚拟机重启后也会自动恢复。

## 工作原理

1. 打开预约网站，你手动完成登录。
2. 进入监控循环：刷新页面 → 选择目标领事馆 → 读取日历上的可用日期。
3. 与上一次快照对比，有变动则发送邮件。
4. 如果开启了自动预定，且发现符合日期范围的时间段，会自动走完预定流程。
5. 等待随机间隔后重复。
6. 如果检测到会话过期（跳转至登录页），会提示重新登录，而不是静默重试。

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
