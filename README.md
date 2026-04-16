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

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/CChen19/us-visa-scheduler.git
cd us-visa-scheduler
pip install -r requirements.txt
```

### 2. Configure

Open `main.py` and edit the top section:

**Consulate**

```python
LOCATION_NAME = "SHANGHAI"  # "SHANGHAI" / "WUHAN" / "SHENYANG"
```

**Email** — use an SMTP app password (e.g. QQ Mail authorization code)

```python
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
EMAIL_SENDER = "your_email@qq.com"
EMAIL_PASSWORD = "your_smtp_app_password"
EMAIL_RECEIVER = "your_receiver@example.com"
```

**Auto-booking** (optional)

```python
BOOKING_CONFIG = {
    "BOOKING_ENABLED": False,
    "EARLIEST_DATE_STR": "2025-08-01",
    "LATEST_DATE_STR": "2025-08-31",
    "DRY_RUN": True,              # True = preview only, False = submit
    "KEEP_BROWSER_OPEN_ON_EXIT": True
}
```

**Applicant name** — search for `Your Name` in `main.py` and replace it with the name shown on the appointment page.

### 3. Run

```bash
python main.py
```

The browser will open. Log in manually, complete any CAPTCHA, then press **Enter** in the terminal. The script takes over from there.

> Tip: use `tmux` or `screen` to keep it running on a remote server.

## How It Works

1. Opens the scheduling site; you log in manually.
2. Enters a monitor loop: refreshes the page, selects the target consulate, reads available dates from the calendar.
3. Compares with the previous snapshot; sends an email if anything changed.
4. If auto-booking is enabled and a date falls within your range, it clicks through the booking flow.
5. Waits a randomized interval before repeating.

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
