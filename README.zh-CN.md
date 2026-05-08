# 美签预约监控工具

📖 [English](./README.md)

自动监控 [usvisascheduling.com](https://www.usvisascheduling.com) 上的美国签证可预约日期，支持邮件提醒和自动预定。

登录步骤需要手动完成验证码，因此脚本需要一个可视化浏览器。以下部署方案在云服务器上运行，通过浏览器访问桌面——无需安装 VNC 客户端或在本地运行。

## 前提条件

- 一台运行 Ubuntu 22.04、内存至少 1 GB 的云服务器（任意服务商均可，如 AWS Lightsail、Oracle Cloud 等）
- 在服务商防火墙中开放 6080 端口（用于桌面访问）
- 可以 SSH 登录到该服务器

## 第一步 — 初始化服务器

SSH 登录服务器，克隆仓库，运行初始化脚本：

```bash
git clone https://github.com/elvinzhou/us-visa-scheduler.git
cd us-visa-scheduler
chmod +x setup.sh && ./setup.sh
```

脚本会提示设置 VNC 密码，然后自动安装以下内容：
- Xfce 桌面 + TigerVNC（仅监听本地）
- noVNC — 通过 6080 端口在浏览器中访问桌面
- Google Chrome
- Python 虚拟环境及所有依赖
- systemd 服务（重启服务器后自动恢复运行）

## 第二步 — 开放 6080 端口

在服务商的防火墙/安全组中，添加一条允许 TCP 6080 端口入站的规则。建议将来源限制为你自己的 IP 以提高安全性。

## 第三步 — 配置 Cloudflare WARP（推荐）

该网站会屏蔽数据中心的 IP 段。WARP 以代理模式运行，将 Chrome 流量通过 Cloudflare 网络转发，同时不影响 SSH 连接：

```bash
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg \
    | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare-warp.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp.gpg] \
https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/cloudflare-warp.list
sudo apt-get update && sudo apt-get install -y cloudflare-warp
warp-cli register
warp-cli mode proxy
warp-cli connect
```

验证是否正常工作——以下命令应返回一个 Cloudflare IP：

```bash
curl --proxy socks5://127.0.0.1:40000 ifconfig.me
```

脚本中的 Chrome 已配置为自动使用 WARP 代理（端口 40000）。

## 第四步 — 配置

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
```

如需修改领事馆或自动预定设置，编辑 `main.py` 顶部：

```python
LOCATION_NAME = "SHENYANG"  # "SHANGHAI" / "WUHAN" / "SHENYANG"

BOOKING_CONFIG = {
    "BOOKING_ENABLED": False,
    "EARLIEST_DATE_STR": "2025-08-01",
    "LATEST_DATE_STR": "2025-08-31",
    "DRY_RUN": True,              # True = 仅模拟，False = 真正提交
    "KEEP_BROWSER_OPEN_ON_EXIT": True
}
```

## 第五步 — 访问桌面

在浏览器中打开 `http://<服务器公网IP>:6080/vnc.html`，输入 VNC 密码，即可在浏览器标签页中看到完整桌面。

## 第六步 — 运行监控脚本

在桌面内打开终端：

```bash
cd us-visa-scheduler
tmux new -s visa
source .venv/bin/activate
python3 main.py
```

Chrome 窗口会自动打开，手动完成登录和验证码，然后在终端按 **Enter**。脚本将接管后续的循环监控。

使用 **Ctrl+B D** 分离 tmux 并关闭浏览器标签页——脚本在后台持续运行。之后如需重新查看：

```bash
tmux attach -t visa
```

## 工作原理

1. 打开预约网站，手动完成登录。
2. 进入监控循环：刷新页面 → 选择目标领事馆 → 读取日历上的可用日期。
3. 与上一次快照对比，有变动则发送邮件。
4. 如果开启了自动预定，且发现符合日期范围的时间段，会自动走完预定流程。
5. 等待随机间隔（3–9 分钟）后重复。
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
