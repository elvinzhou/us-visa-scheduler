# Visa Appointment Watcher

📖 [简体中文](./README.zh-CN.md)

Automatically monitors available U.S. visa appointment dates on [usvisascheduling.com](https://www.usvisascheduling.com), with email alerts and optional auto-booking.

The login step requires completing a CAPTCHA manually, so the script needs a visible browser. The setup below runs it on a cloud VM with a browser-accessible desktop — no VNC client or local install needed.

## Prerequisites

- A Ubuntu 22.04 VM with at least 1 GB RAM (any provider — AWS Lightsail, Oracle Cloud, etc.)
- Port 6080 open in your provider's firewall for the desktop
- SSH access to the VM

## Step 1 — Bootstrap the VM

SSH into your VM, clone the repo, and run the setup script:

```bash
git clone https://github.com/elvinzhou/us-visa-scheduler.git
cd us-visa-scheduler
chmod +x setup.sh && ./setup.sh
```

The script prompts for a VNC password then automatically installs:
- Xfce desktop + TigerVNC (localhost only)
- noVNC — browser-accessible desktop on port 6080
- Google Chrome
- Python venv with all dependencies
- systemd services so everything restarts on reboot

## Step 2 — Open port 6080

In your provider's firewall/security group, add an inbound TCP rule for port 6080. Restrict the source to your IP for better security.

## Step 3 — Set up Cloudflare WARP (recommended)

The site blocks datacenter IP ranges. WARP routes Chrome traffic through Cloudflare's network to avoid this. Install and enable it in proxy mode so SSH is unaffected:

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

Verify it's working — this should return a Cloudflare IP:

```bash
curl --proxy socks5://127.0.0.1:40000 ifconfig.me
```

Chrome is already configured to use the WARP proxy (port 40000) in the script.

## Step 4 — Configure

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
nano .env
```

```dotenv
# Applicant name exactly as shown on the scheduling page
APPLICANT_NAME=Your Full Name

# Email notifications — supports multiple comma-separated receivers
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_smtp_app_password
EMAIL_RECEIVER=receiver1@example.com,receiver2@example.com

# Optional — defaults shown
# SMTP_SERVER=smtp.qq.com
# SMTP_PORT=465
```

To change the consulate or auto-booking settings, edit the top of `main.py`:

```python
LOCATION_NAME = "SHENYANG"  # "SHANGHAI" / "WUHAN" / "SHENYANG"

BOOKING_CONFIG = {
    "BOOKING_ENABLED": False,
    "EARLIEST_DATE_STR": "2025-08-01",
    "LATEST_DATE_STR": "2025-08-31",
    "DRY_RUN": True,              # True = preview only, False = submit
    "KEEP_BROWSER_OPEN_ON_EXIT": True
}
```

## Step 5 — Access the desktop

Open `http://<your-vm-ip>:6080/vnc.html` in a browser and enter your VNC password. You'll see a full desktop in the tab.

## Step 6 — Run the scheduler

In a terminal inside the desktop:

```bash
cd us-visa-scheduler
tmux new -s visa
source .venv/bin/activate
python3 main.py
```

A Chrome window will open. Log in manually and complete the CAPTCHA, then press **Enter** in the terminal. The script takes over and monitors in a loop.

Detach tmux with **Ctrl+B D** and close the browser tab — the scheduler keeps running in the background. To reattach later:

```bash
tmux attach -t visa
```

## How It Works

1. Opens the scheduling site; you log in manually.
2. Enters a monitor loop: refreshes the page, selects the target consulate, reads available dates from the calendar.
3. Compares with the previous snapshot; sends an email if anything changed.
4. If auto-booking is enabled and a date falls within your configured range, it clicks through the booking flow automatically.
5. Waits a randomized interval (3–9 min) before repeating.
6. If session expiry is detected (redirected to login), prompts for re-login instead of silently retrying.

## Email Example

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

## Disclaimer

- For personal / educational use only.
- The author(s) are not responsible for any consequences of using this tool.
- Manual login is required on first run and after session expiry.
- Stable internet connection recommended.

## Acknowledgements

Based on the original work by [SYuan03](https://github.com/SYuan03/VisaAppointmentWatcher).

## License

[MIT](./LICENSE)
