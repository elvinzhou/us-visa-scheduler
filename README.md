# Visa Appointment Watcher

📖 [简体中文](./README.zh-CN.md)

Automatically monitors available U.S. visa appointment dates on [usvisascheduling.com](https://www.usvisascheduling.com), with email alerts and optional auto-booking.

Login and CAPTCHA solving are fully automated — the script uses your credentials and OpenAI's GPT-4o-mini to handle the login flow. A visible browser is still required so the site doesn't detect headless automation. Run it on a machine with a display: WSL2 on Windows, a Raspberry Pi, or any Ubuntu desktop/server.

## Prerequisites

- WSL2 (Windows 11 with WSLg), Raspberry Pi OS, or Ubuntu 22.04+
- Git installed

## Step 1 — Clone and bootstrap

```bash
git clone https://github.com/elvinzhou/us-visa-scheduler.git
cd us-visa-scheduler
chmod +x setup.sh && ./setup.sh
```

The script installs:
- Google Chrome (x86-64) or Chromium (ARM / Raspberry Pi)
- Python venv with all dependencies
- tmux

> **WSL note:** WSLg (Windows 11 build 22000+) is required for the browser window to appear. On Windows 10 WSL2 install an X server such as [VcXsrv](https://sourceforge.net/projects/vcxsrv/) and run `export DISPLAY=:0` before starting the script.

## Step 2 — Configure

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
nano .env
```

```dotenv
# Applicant name exactly as shown on the scheduling page
APPLICANT_NAME=Your Full Name

# Visa site credentials
VISA_USERNAME=your_visa_site_email
VISA_PASSWORD=your_visa_site_password

# Security question answers (optional — only needed if your account uses them)
# SECURITY_A1=your_answer_1
# SECURITY_A2=your_answer_2
# SECURITY_A3=your_answer_3

# OpenAI API key — used to solve the login CAPTCHA automatically
OPENAI_API_KEY=sk-...

# Email notifications — supports multiple comma-separated receivers
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_smtp_app_password
EMAIL_RECEIVER=receiver1@example.com,receiver2@example.com

# Optional — defaults shown
# SMTP_SERVER=smtp.qq.com
# SMTP_PORT=465

# Consulate to monitor: SHANGHAI / WUHAN / SHENYANG (default: SHENYANG)
# LOCATION_NAME=SHENYANG

# Auto-booking settings (all optional — defaults shown)
# BOOKING_ENABLED=false         # set to "true" to enable auto-booking
# EARLIEST_DATE_STR=2025-08-01  # earliest acceptable appointment date
# LATEST_DATE_STR=2025-08-31    # latest acceptable appointment date
# DRY_RUN=true                  # "false" to actually submit; "true" for preview only
# KEEP_BROWSER_OPEN_ON_EXIT=true
```

## Step 3 — Run the scheduler

```bash
tmux new -s visa
source .venv/bin/activate
python3 main.py
```

A Chrome window will open on your screen. The script automatically logs in and solves the CAPTCHA, then enters the monitoring loop.

Detach tmux with **Ctrl+B D** — the scheduler keeps running in the background. To reattach later:

```bash
tmux attach -t visa
```

## How It Works

1. Opens the scheduling site and automatically logs in, solving the CAPTCHA via GPT-4o-mini.
2. Enters a monitor loop: refreshes the page, selects the target consulate, reads available dates via an intercepted API response (falls back to DOM scraping on timeout).
3. Compares with the previous snapshot; sends an email if anything changed.
4. If auto-booking is enabled and a date falls within your configured range, it clicks through the booking flow automatically.
5. Waits a randomized interval (3–5 min normally, 7–9 min for occasional longer rests) before repeating.
6. If session expiry is detected (redirected to login), automatically re-logs in instead of silently retrying.

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
- A visible browser window is required — headless mode is not supported.
- Stable internet connection recommended.

## Acknowledgements

Based on the original work by [SYuan03](https://github.com/SYuan03/VisaAppointmentWatcher).

## License

[MIT](./LICENSE)
