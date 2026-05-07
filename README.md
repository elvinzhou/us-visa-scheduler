# Visa Appointment Watcher

📖 [简体中文](./README.zh-CN.md)

Automatically monitor available U.S. visa appointment dates on [usvisascheduling.com](https://www.usvisascheduling.com), with email alerts and optional auto-booking.

## Features

- Real-time monitoring of visa appointment availability
- Supports multiple consulates: Shanghai, Wuhan, Shenyang
- Randomized check intervals (3–9 min) to reduce detection risk
- Email notifications on date changes (new / removed slots)
- Auto-booking within a configurable date range (with dry-run safety mode)
- Terminal countdown timer between checks
- Uses `undetected_chromedriver` to bypass bot detection
- Manual login step for CAPTCHA / 2FA handling
- Session expiry detection with re-login prompt

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/elvinzhou/us-visa-scheduler.git
cd us-visa-scheduler
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

**Consulate** — edit `main.py`:

```python
LOCATION_NAME = "SHANGHAI"  # "SHANGHAI" / "WUHAN" / "SHENYANG"
```

**Auto-booking** — also in `main.py` (optional):

```python
BOOKING_CONFIG = {
    "BOOKING_ENABLED": False,
    "EARLIEST_DATE_STR": "2025-08-01",
    "LATEST_DATE_STR": "2025-08-31",
    "DRY_RUN": True,              # True = preview only, False = submit
    "KEEP_BROWSER_OPEN_ON_EXIT": True
}
```

**Environment variables** — copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```dotenv
# Applicant name exactly as shown on the scheduling page
APPLICANT_NAME=Your Full Name

# Email credentials (SMTP app password, e.g. QQ Mail authorization code)
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_smtp_app_password
EMAIL_RECEIVER=your_receiver@example.com

# Optional — defaults shown
# SMTP_SERVER=smtp.qq.com
# SMTP_PORT=465
```

The `.env` file is gitignored and never committed.

### 3. Run

```bash
source .venv/bin/activate
python main.py
```

The browser will open. Log in manually, complete any CAPTCHA, then press **Enter** in the terminal. The script takes over from there.

> Tip: use `tmux` or `screen` to keep it running after you close the terminal.

## Deploying to Oracle Cloud (free, browser desktop)

The login step requires a visible browser for CAPTCHA. The included `setup.sh` provisions a full desktop environment on an Oracle Cloud **Always Free** Ubuntu 22.04 VM, accessible from any browser via noVNC — no VNC client needed.

### 1. Provision the VM

Sign up at [cloud.oracle.com](https://cloud.oracle.com) and create a free VM:
- **Shape**: `VM.Standard.E2.1.Micro` (AMD x86, 1 OCPU / 1 GB RAM) — easiest Chrome compatibility
- **Image**: Ubuntu 22.04
- Download the SSH key during provisioning

### 2. Run the bootstrap script

Open **Cloud Shell** (the `>_` icon in the OCI top nav), SSH into your VM, then:

```bash
git clone https://github.com/elvinzhou/us-visa-scheduler.git
cd us-visa-scheduler
chmod +x setup.sh && ./setup.sh
```

The script will prompt for a VNC password, then install and configure everything automatically (desktop, noVNC, Chrome, Python deps, systemd services).

### 3. Open port 6080 in OCI

In the OCI Console:
> Networking → Virtual Cloud Networks → your VCN → Security Lists → Default Security List → Add Ingress Rule
> - Source CIDR: `0.0.0.0/0` (or restrict to your IP for tighter security)
> - Protocol: TCP, Port: `6080`

### 4. Access the desktop

Open `http://<your-vm-ip>:6080/vnc.html` in a browser and enter your VNC password. You'll see a full Xfce desktop.

### 5. Run the scheduler

In the VM desktop, open a terminal:

```bash
cd us-visa-scheduler
cp .env.example .env   # fill in your values
tmux new -s visa
source .venv/bin/activate
python3 main.py
```

Complete the CAPTCHA login in the browser that opens, press **Enter**, then detach tmux with **Ctrl+B D** and close the browser tab. The scheduler keeps running in the background and survives VM reboots.

## How It Works

1. Opens the scheduling site; you log in manually.
2. Enters a monitor loop: refreshes the page, selects the target consulate, reads available dates from the calendar.
3. Compares with the previous snapshot; sends an email if anything changed.
4. If auto-booking is enabled and a date falls within your range, it clicks through the booking flow.
5. Waits a randomized interval before repeating.
6. If a session expiry is detected (redirected to login), prompts for re-login instead of silently retrying.

## Email Example

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

## Disclaimer

- For personal / educational use only.
- The author(s) are not responsible for any consequences of using this tool.
- Manual login may be required after session expiry.
- Stable internet connection recommended.

## Acknowledgements

This project is based on the original work by [SYuan03](https://github.com/SYuan03/VisaAppointmentWatcher). Thanks for the great foundation!

## License

[MIT](./LICENSE)
