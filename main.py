# -*- coding: utf-8 -*-
from datetime import date, datetime
from email.utils import formataddr
import os
import random
import traceback
import base64
from dotenv import load_dotenv
load_dotenv()
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException, NoSuchElementException
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.header import Header
from openai import OpenAI

# --- 全局配置 ---
# 选择您要监控的领事馆: "SHANGHAI" / "WUHAN" / "SHENYANG"
LOCATION_NAME = os.environ.get("LOCATION_NAME", "SHENYANG")

LOCATIONS = {
    "SHANGHAI": {"name": "SHANGHAI", "id": "096bf614-b0db-ec11-a7b4-001dd80234f6"},
    "WUHAN": {"name": "WUHAN", "id": "7b6af614-b0db-ec11-a7b4-001dd80234f6"},
    "SHENYANG": {"name": "SHENYANG", "id": "0f6bf614-b0db-ec11-a7b4-001dd80234f6"},
}
LOCATION_VALUE_ID = LOCATIONS[LOCATION_NAME]["id"]

# --- 自动预定配置 ---
BOOKING_CONFIG = {
    "BOOKING_ENABLED": os.environ.get("BOOKING_ENABLED", "false").lower() == "true",
    "EARLIEST_DATE_STR": os.environ.get("EARLIEST_DATE_STR", "2025-08-01"),
    "LATEST_DATE_STR": os.environ.get("LATEST_DATE_STR", "2025-08-31"),
    "DRY_RUN": os.environ.get("DRY_RUN", "true").lower() != "false",
    "KEEP_BROWSER_OPEN_ON_EXIT": os.environ.get("KEEP_BROWSER_OPEN_ON_EXIT", "true").lower() != "false",
}

APPLICANT_NAME = os.environ["APPLICANT_NAME"]

# 邮件配置
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVERS = [r.strip() for r in os.environ["EMAIL_RECEIVER"].split(",")]

# 登录配置
PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".visa_scheduler_profile")
VISA_USERNAME = os.environ["VISA_USERNAME"]
VISA_PASSWORD = os.environ["VISA_PASSWORD"]
SECURITY_ANSWERS = {
    "#kba1_response": os.environ.get("SECURITY_A1", ""),
    "#kba2_response": os.environ.get("SECURITY_A2", ""),
    "#kba3_response": os.environ.get("SECURITY_A3", ""),
}

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

MAX_RETRIES = 5
RETRY_DELAY = 2

# JS hook that intercepts the schedule API response
_API_HOOK_JS = """
if (!window.__visaHookInstalled) {
    window.__visaHookInstalled = true;
    window.__slotFound = null;
    window.__slotDays = [];

    const TARGET = '/custom-actions/?route=/api/v1/schedule-group/get-family-consular-schedule-days';

    function _processPayload(url, text) {
        if (!url || url.indexOf(TARGET) === -1) return;
        try {
            var json = JSON.parse(text);
            var days = json && json.ScheduleDays;
            if (Array.isArray(days) && days.length > 0) {
                window.__slotFound = true;
                window.__slotDays = days;
            } else {
                window.__slotFound = false;
                window.__slotDays = [];
            }
        } catch(e) {}
    }

    var _origFetch = window.fetch;
    window.fetch = function() {
        var args = Array.prototype.slice.call(arguments);
        var url = (args[0] && args[0].toString) ? args[0].toString() : '';
        return _origFetch.apply(this, args).then(function(response) {
            if (url.indexOf(TARGET) !== -1) {
                response.clone().text().then(function(text) {
                    _processPayload(url, text);
                }).catch(function(){});
            }
            return response;
        });
    };

    var _origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.__visaUrl = url;
        return _origOpen.apply(this, arguments);
    };
    var _origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function() {
        var self = this;
        this.addEventListener('load', function() {
            _processPayload(self.__visaUrl, self.responseText);
        });
        return _origSend.apply(this, arguments);
    };
}
"""


# --- 邮件发送函数 ---
def send_notification_email(added_dates, removed_dates, all_dates):
    if not added_dates and not removed_dates:
        return
    subject = f"【签证监控】{LOCATION_NAME} F1签证日期变动！"
    body_lines = [f"领事馆: {LOCATION_NAME}"]
    if added_dates:
        body_lines.append("\n新增的可预约日期:")
        for d in sorted(added_dates):
            body_lines.append(f"  ✅ {d}")
    if removed_dates:
        body_lines.append("\n不再可用的日期:")
        for d in sorted(removed_dates):
            body_lines.append(f"  ❌ {d}")
    body_lines.append("\n\n当前所有可预约日期:")
    body_lines.append("\n".join([f"  - {d}" for d in sorted(all_dates)]) if all_dates else "  (暂无可用日期)")

    if BOOKING_CONFIG["BOOKING_ENABLED"] and added_dates:
        earliest = BOOKING_CONFIG["EARLIEST_DATE_STR"]
        latest = BOOKING_CONFIG["LATEST_DATE_STR"]
        in_range = sorted([d for d in added_dates if earliest <= d <= latest])
        if in_range:
            mode = "模拟预定 (Dry Run)" if BOOKING_CONFIG["DRY_RUN"] else "真实预定"
            body_lines.append(f"\n\n⚡ 自动预定已启用 ({mode})")
            body_lines.append(f"正在尝试预定: {in_range[0]}")
            body_lines.append("请等待预定确认邮件，无需手动操作。")
        else:
            body_lines.append(f"\n\n自动预定已启用，但新增日期不在设定范围 ({earliest} 至 {latest}) 内，未触发预定。")
            body_lines.append("如需手动预约，请访问: https://www.usvisascheduling.com/zh-CN/schedule/")
    else:
        body_lines.append("\n\n请尽快手动前往预约: https://www.usvisascheduling.com/zh-CN/schedule/")

    _send_email(subject, "\n".join(body_lines))

def send_booking_confirmation_email(booked_date, booked_time):
    mode = "模拟" if BOOKING_CONFIG['DRY_RUN'] else "成功"
    subject = f"【签证预定{mode}】{LOCATION_NAME} F1签证已{mode}预定！"
    body = (
        f"领事馆: {LOCATION_NAME}\n"
        f"预定状态: {mode.upper()}\n\n"
        f"已为您自动选择并{mode}提交了以下时间：\n"
        f"  📅 日期: {booked_date}\n"
        f"  🕒 时间: {booked_time}\n\n"
    )
    if BOOKING_CONFIG['DRY_RUN']:
        body += "注意：当前为安全模式(Dry Run)，未点击最终提交按钮。\n"
    else:
        body += "请立即登录官方网站确认预定结果！\n"
    if BOOKING_CONFIG['KEEP_BROWSER_OPEN_ON_EXIT']:
        body += "\n脚本已执行完毕，浏览器保持打开状态供您检查。"
    _send_email(subject, body)

def send_relogin_email():
    _send_email(
        f"【签证监控】{LOCATION_NAME} 自动登录失败，需要人工干预",
        f"领事馆: {LOCATION_NAME}\n\n自动登录重试{MAX_RETRIES}次后仍然失败，请检查账号密码或安全问题答案配置。",
    )

def send_status_email(check_count):
    _send_email(
        f"【签证监控】{LOCATION_NAME} 运行正常，暂无可用日期",
        f"领事馆: {LOCATION_NAME}\n\n监控脚本运行正常，过去6小时内共检查 {check_count} 次，暂未发现可用日期。",
    )

def _send_email(subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = formataddr((f"{LOCATION_NAME}签证监控", EMAIL_SENDER))
    msg["To"] = ", ".join(EMAIL_RECEIVERS)
    msg["Subject"] = Header(subject, 'utf-8')

    def _try_send():
        ctx = ssl.create_default_context()
        try:
            print(f"尝试 SMTP_SSL 连接 {SMTP_SERVER}:{SMTP_PORT}...")
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx, timeout=30)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVERS, msg.as_string())
            server.quit()
            return
        except Exception as e1:
            print(f"SMTP_SSL 失败: {e1}")

        starttls_port = 587
        try:
            print(f"尝试 STARTTLS 连接 {SMTP_SERVER}:{starttls_port}...")
            server = smtplib.SMTP(SMTP_SERVER, starttls_port, timeout=30)
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVERS, msg.as_string())
            server.quit()
            return
        except Exception as e2:
            print(f"STARTTLS 失败: {e2}")

        raise RuntimeError("所有连接方式均失败")

    for attempt in range(1, 4):
        try:
            print(f"正在连接邮件服务器 (第 {attempt} 次)...")
            _try_send()
            print(f"邮件已成功发送至 {', '.join(EMAIL_RECEIVERS)}")
            return
        except Exception as e:
            print(f"邮件发送失败 (第 {attempt} 次)，错误: {e}")
            if attempt < 3:
                time.sleep(5 * attempt)
    print("邮件发送最终失败，已跳过。")


_TRANSIENT_KEYWORDS = ("timed out", "timeout", "connection", "cloudflare", "aborted", "not attached", "read timed out")

def _is_transient_error(exc):
    return any(kw in str(exc).lower() for kw in _TRANSIENT_KEYWORDS)

def _is_cloudflare_page(driver):
    try:
        title = driver.title.lower()
        return "just a moment" in title or "cloudflare" in title
    except Exception:
        return False

def _navigate(driver, url):
    """Navigate to url, retrying indefinitely with exponential backoff starting at 30s."""
    delay = 30
    attempt = 0
    while True:
        attempt += 1
        try:
            driver.get(url)
            if _is_cloudflare_page(driver):
                raise WebDriverException("Cloudflare challenge page detected")
            return
        except Exception as e:
            print(f"页面加载失败 (第{attempt}次): {e}\n等待{delay}秒后重试...")
            time.sleep(delay)
            delay *= 2


def countdown_timer(total_seconds):
    print()
    while total_seconds > 0:
        mins, secs = divmod(total_seconds, 60)
        print(f'下一次检查将在 {mins:02d}:{secs:02d} 后开始...', end='\r')
        time.sleep(1)
        total_seconds -= 1
    print("\n倒计时结束。                                   ")


# --- 新增：等候室、登录、API拦截 ---

def handle_waiting_room(driver):
    while True:
        try:
            style = driver.find_element(By.TAG_NAME, "body").get_attribute("style") or ""
            if "waiting_room_background" not in style:
                return
            print("检测到候客室，等待5秒后重试...")
            time.sleep(5)
        except Exception:
            return


def _is_login_page(driver):
    try:
        url = driver.current_url.lower()
        if "login" in url or "b2clogin" in url or "microsoftonline" in url:
            return True
        driver.find_element(By.ID, "signInName")
        return True
    except NoSuchElementException:
        return False


def _refresh_captcha(driver):
    """Click the captcha refresh button to get a new image, falling back to a full page refresh."""
    try:
        driver.find_element(By.ID, "captchaRefreshImage").click()
        print("已点击验证码刷新按钮，等待新验证码...")
    except NoSuchElementException:
        driver.refresh()
        print("未找到验证码刷新按钮，已刷新页面。")
    time.sleep(RETRY_DELAY)


def _solve_captcha(driver):
    seen_srcs = set()
    for attempt in range(MAX_RETRIES):
        try:
            img = WebDriverWait(driver, 45).until(
                EC.presence_of_element_located((By.ID, "captchaImage"))
            )
            src = img.get_attribute("src") or ""
            if not src or src in seen_srcs:
                time.sleep(RETRY_DELAY)
                continue
            seen_srcs.add(src)

            img_b64 = img.screenshot_as_base64
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                        {"type": "text", "text": "Please transcribe the characters from this captcha image. Respond with only those characters in UPPERCASE, no additional text."},
                    ],
                }],
                max_tokens=20,
            )
            text = response.choices[0].message.content.strip()
            if len(text) > 5:
                print(f"验证码识别结果异常（{len(text)}字符: {text}），刷新重试...")
                _refresh_captcha(driver)
                continue
            return text
        except Exception as e:
            print(f"验证码识别第 {attempt + 1} 次失败: {e}")
            time.sleep(RETRY_DELAY)
    return None


def do_login(driver):
    print("检测到登录页面，开始自动登录...")

    # Stage 1: credentials + captcha
    logged_in = False
    for attempt in range(MAX_RETRIES):
        # On the 3rd attempt the auth service may be having a transient error.
        # Try navigating straight to the schedule page — if the session cookie is
        # still valid we land there directly; if not, we get redirected to login
        # and fall through to the normal credential flow on subsequent attempts.
        if attempt == 2:
            print("第3次尝试：直接导航至预约页面，绕过认证服务...")
            driver.get("https://www.usvisascheduling.com/zh-CN/schedule/")
            try:
                WebDriverWait(driver, 15).until(lambda d: any(
                    kw in d.current_url.lower()
                    for kw in ("usvisascheduling.com/zh-cn/schedule", "login", "b2clogin", "microsoftonline")
                ))
            except TimeoutException:
                pass
            if not _is_login_page(driver):
                logged_in = True
                break
            print("直接导航后仍在登录页面，继续尝试凭据登录...")

        try:
            username_field = WebDriverWait(driver, 45).until(
                EC.presence_of_element_located((By.ID, "signInName"))
            )
            username_field.clear()
            username_field.send_keys(VISA_USERNAME)

            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(VISA_PASSWORD)

            captcha_text = _solve_captcha(driver)
            if not captcha_text:
                print(f"验证码识别失败，第 {attempt + 1} 次重试...")
                _refresh_captcha(driver)
                continue

            print(f"验证码识别结果: {captcha_text}")
            captcha_input = driver.find_element(By.ID, "extension_atlasCaptchaResponse")
            captcha_input.clear()
            captcha_input.send_keys(captcha_text)

            driver.find_element(By.ID, "continue").click()

            # Wait for the page to settle on a definitive state.
            # A point-in-time check after a short sleep mis-detects a slow
            # redirect back to login as success (signInName not yet in DOM).
            try:
                WebDriverWait(driver, 15).until(lambda d: (
                    bool(d.find_elements(By.ID, "signInName")) or
                    bool(d.find_elements(By.CSS_SELECTOR, "#kba1_response, #kba2_response, #kba3_response")) or
                    ("usvisascheduling.com" in d.current_url and "login" not in d.current_url.lower())
                ))
            except TimeoutException:
                pass

            if driver.find_elements(By.ID, "signInName"):
                print(f"登录未成功（页面返回至登录页），第 {attempt + 1} 次重试...")
                if driver.find_elements(By.XPATH, "//*[contains(text(), 'Captcha Validation is not Successful')]"):
                    _refresh_captcha(driver)  # captcha error shown — get a fresh image
            else:
                logged_in = True
                break
        except Exception as e:
            print(f"登录第 {attempt + 1} 次出错: {e}")
            time.sleep(RETRY_DELAY)

    if not logged_in:
        print("凭据登录失败，已达最大重试次数。")
        send_relogin_email()
        return False

    # Stage 2: security questions (may or may not appear)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#kba1_response, #kba2_response, #kba3_response"))
        )
        print("检测到安全问题页面，正在填写...")
        for selector, answer in SECURITY_ANSWERS.items():
            if not answer:
                continue
            try:
                field = driver.find_element(By.CSS_SELECTOR, selector)
                if field.is_displayed():
                    field.clear()
                    field.send_keys(answer)
            except NoSuchElementException:
                pass

        driver.find_element(By.ID, "continue").click()
        WebDriverWait(driver, 30).until(
            lambda d: "usvisascheduling.com" in d.current_url and "login" not in d.current_url.lower()
        )
    except TimeoutException:
        pass  # No security questions or already navigated away

    print("登录成功！")
    return True


def inject_api_hook(driver):
    driver.execute_script(_API_HOOK_JS)


def _parse_schedule_days(raw_days):
    dates = set()
    for entry in raw_days:
        try:
            if isinstance(entry, str):
                dates.add(entry[:10])  # take YYYY-MM-DD prefix
            elif isinstance(entry, dict):
                for key in ("Date", "date", "AvailableDate", "scheduleDate"):
                    if key in entry:
                        dates.add(str(entry[key])[:10])
                        break
        except Exception:
            pass
    return dates


def get_available_dates(driver, wait):
    """Select the location, wait for the API response via the injected hook,
    and return a set of ISO date strings. Falls back to DOM scraping on timeout."""

    # Reset hook state before triggering the API call
    driver.execute_script("window.__slotFound = null; window.__slotDays = [];")

    wait.until(EC.presence_of_element_located((By.ID, "post_select")))
    Select(driver.find_element(By.ID, "post_select")).select_by_value(LOCATION_VALUE_ID)
    print(f"已选择领事馆: {LOCATION_NAME}，等待API响应...")

    deadline = time.time() + 30
    while time.time() < deadline:
        slot_found = driver.execute_script("return window.__slotFound;")
        if slot_found is True:
            raw = driver.execute_script("return window.__slotDays;") or []
            dates = _parse_schedule_days(raw)
            print(f"API拦截成功，发现 {len(dates)} 个可用日期。")
            return dates
        if slot_found is False:
            print("API拦截成功，当前无可用日期。")
            return set()
        time.sleep(0.5)

    # Fallback: DOM scraping
    print("API响应超时，回退到DOM解析...")
    available_dates = set()
    try:
        wait.until(lambda d: "正在加载" not in d.find_element(By.TAG_NAME, "body").text)
        error_rows = driver.find_elements(By.ID, "error_row")
        if error_rows and error_rows[0].is_displayed():
            error_text = error_rows[0].text.strip()
            if "无可用时段" not in error_text:
                print(f"页面返回错误: {error_text}")
        else:
            day_cells = driver.find_elements(By.CSS_SELECTOR, "td[data-handler='selectDay'].greenday")
            print(f"DOM解析完成，发现 {len(day_cells)} 个可用日期。")
            for cell in day_cells:
                try:
                    day = cell.find_element(By.CSS_SELECTOR, "a.ui-state-default").text
                    month = int(cell.get_attribute("data-month")) + 1
                    year = int(cell.get_attribute("data-year"))
                    available_dates.add(date(year, month, int(day)).isoformat())
                except Exception as e:
                    print(f"解析日期单元格时出错: {e}")
    except TimeoutException:
        print("DOM解析也超时，跳过本轮。")
    return available_dates


# --- 主程序 ---
def main():
    options = uc.ChromeOptions()
    for arg in ["--no-first-run", "--no-service-autorun", "--password-store=basic"]:
        options.add_argument(arg)
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    driver = uc.Chrome(options=options)

    booking_completed_successfully = False

    try:
        wait = WebDriverWait(driver, 60)
        current_dates = set()

        SHORT_WAIT_MIN, SHORT_WAIT_MAX = 3, 5
        LONG_REST_MIN, LONG_REST_MAX = 7, 9
        checks_until_long_rest = random.randint(4, 7)
        last_status_email_time = time.time()
        checks_since_last_status = 0

        if BOOKING_CONFIG['BOOKING_ENABLED']:
            print("\n--- 自动预定已启用 ---")
            print(f"可接受日期范围: {BOOKING_CONFIG['EARLIEST_DATE_STR']} 至 {BOOKING_CONFIG['LATEST_DATE_STR']}")
            print(f"模式: {'安全模式 (Dry Run)' if BOOKING_CONFIG['DRY_RUN'] else '真实预定模式'}")
            print("------------------------\n")

        _navigate(driver, "https://www.usvisascheduling.com/zh-CN/schedule/")

        server_backoff = 60

        while True:
            try:
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始新一轮检查...")

                # Dismiss any alert already present before refreshing — an
                # unhandled alert causes driver.refresh() to throw WebDriverException.
                # alert.dismiss() itself can throw if the page is already navigating,
                # so wrap it separately and always continue once an alert is detected.
                alert_present = False
                try:
                    alert = driver.switch_to.alert
                    alert_present = True
                    print(f"检测到弹窗(刷新前): \"{alert.text}\"，已自动关闭。")
                    try:
                        alert.dismiss()
                    except Exception:
                        pass
                except Exception:
                    pass
                if alert_present:
                    countdown_timer(60)
                    continue

                driver.refresh()
                print("页面已刷新，等待页面加载...")
                if _is_cloudflare_page(driver):
                    raise WebDriverException("Cloudflare challenge page detected")

                # Dismiss JS alert that appeared during/after the refresh
                try:
                    alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                    print(f"检测到弹窗: \"{alert.text}\"，已自动关闭。")
                    alert.dismiss()
                    countdown_timer(60)
                    continue
                except TimeoutException:
                    pass

                # 1. Waiting room
                handle_waiting_room(driver)

                # 2. Auto-login if needed
                if _is_login_page(driver):
                    if not do_login(driver):
                        countdown_timer(5 * 60)
                        continue
                    # Login redirects to the landing page; navigate to the schedule page.
                    _navigate(driver, "https://www.usvisascheduling.com/zh-CN/schedule/")

                # 3. Inject API hook
                inject_api_hook(driver)

                # 4. Wait for applicant name (confirms we're on the right page)
                wait.until(EC.visibility_of_element_located((By.XPATH, f"//label[text()='{APPLICANT_NAME}']")))
                print("申请人加载成功。")

                # 5. Get available dates via API hook (with DOM fallback)
                available_dates = get_available_dates(driver, wait)

                if available_dates != current_dates:
                    print("---!!! 日期有变动 !!! ---")
                    added = available_dates - current_dates
                    removed = current_dates - available_dates
                    send_notification_email(added, removed, available_dates)
                    current_dates = available_dates
                else:
                    print(f"日期无变化。当前可用: {sorted(list(current_dates)) if current_dates else '无'}")

                # --- 自动预定逻辑 ---
                if BOOKING_CONFIG["BOOKING_ENABLED"] and current_dates:
                    earliest_date = datetime.strptime(BOOKING_CONFIG["EARLIEST_DATE_STR"], "%Y-%m-%d").date()
                    latest_date = datetime.strptime(BOOKING_CONFIG["LATEST_DATE_STR"], "%Y-%m-%d").date()

                    potential_dates = sorted([
                        d for d in current_dates
                        if earliest_date <= datetime.strptime(d, "%Y-%m-%d").date() <= latest_date
                    ])

                    if not potential_dates:
                        print(f"有可用日期，但不在设定的 {earliest_date} 到 {latest_date} 范围内，不进行预定。")
                    else:
                        book_date_str = potential_dates[0]
                        book_date_obj = datetime.strptime(book_date_str, "%Y-%m-%d").date()
                        print(f"---!!! 发现符合条件的目标日期: {book_date_str} !!!---")
                        print("开始执行自动预定流程...")

                        day_to_click = str(book_date_obj.day)
                        month_to_click = str(book_date_obj.month - 1)
                        year_to_click = str(book_date_obj.year)

                        target_cell_xpath = f"//td[@data-year='{year_to_click}' and @data-month='{month_to_click}']//a[text()='{day_to_click}']"
                        target_cell_link = wait.until(EC.element_to_be_clickable((By.XPATH, target_cell_xpath)))
                        print(f"步骤 1/4: 正在点击日期 {book_date_str}...")
                        target_cell_link.click()

                        print("步骤 2/4: 等待并选择时间...")
                        first_time_radio = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#time_select input[name='schedule-entries']")))
                        booked_time = first_time_radio.find_element(By.XPATH, "..").text.strip()
                        print(f"选择最早时间点: {booked_time}")
                        first_time_radio.click()

                        print("步骤 3/4: 等待提交按钮...")
                        submit_button = wait.until(EC.element_to_be_clickable((By.ID, "submitbtn")))

                        print("步骤 4/4: 执行提交...")
                        if not BOOKING_CONFIG["DRY_RUN"]:
                            print("真实模式：正在点击提交按钮！")
                            submit_button.click()
                            print("--- 预定已提交！---")
                        else:
                            print("安全模式 (Dry Run)：跳过最终提交步骤。")
                            print("--- 模拟预定完成 ---")

                        send_booking_confirmation_email(book_date_str, booked_time)
                        print("预定流程执行完毕，已跳出监控循环。")
                        booking_completed_successfully = True
                        break

                server_backoff = 60  # successful check — reset transient-error backoff
                checks_since_last_status += 1

                if not current_dates and time.time() - last_status_email_time >= 6 * 3600:
                    send_status_email(checks_since_last_status)
                    last_status_email_time = time.time()
                    checks_since_last_status = 0

                if not booking_completed_successfully:
                    checks_until_long_rest -= 1
                    if checks_until_long_rest <= 0:
                        rest_secs = random.randint(LONG_REST_MIN * 60, LONG_REST_MAX * 60)
                        print(f"\n--- 进入长时休眠 {rest_secs // 60}分{rest_secs % 60:02d}秒... ---")
                        countdown_timer(rest_secs)
                        checks_until_long_rest = random.randint(4, 7)
                    else:
                        wait_secs = random.randint(SHORT_WAIT_MIN * 60, SHORT_WAIT_MAX * 60)
                        print(f"\n--- 常规等待 {wait_secs // 60}分{wait_secs % 60:02d}秒... ---")
                        countdown_timer(wait_secs)

            except UnexpectedAlertPresentException as e:
                print(f"本轮检查出现错误: {e}")
                try:
                    driver.switch_to.alert.dismiss()
                    print("弹窗已关闭，等待1分钟后重试。")
                except Exception:
                    pass
                countdown_timer(60)
            except Exception as e:
                print(f"本轮检查出现错误: {e}")
                traceback.print_exc()
                try:
                    current_url = driver.current_url
                except Exception:
                    current_url = ""
                if "usvisascheduling.com" not in current_url or "login" in current_url.lower():
                    print("检测到会话已过期，尝试重新登录...")
                    countdown_timer(10)
                elif _is_transient_error(e) or _is_cloudflare_page(driver):
                    print(f"检测到服务器临时错误，等待 {server_backoff // 60} 分{server_backoff % 60:02d}秒后重试...")
                    countdown_timer(server_backoff)
                    server_backoff *= 2
                else:
                    server_backoff = 60
                    print("将等待1分钟后重试。")
                    countdown_timer(60)

        if booking_completed_successfully:
            print("\n" + "=" * 50)
            print("脚本已完成预定任务。")
            if BOOKING_CONFIG.get("KEEP_BROWSER_OPEN_ON_EXIT", False):
                print("浏览器将保持打开状态供您检查。")
                input("您可以随时按 Enter 键来关闭浏览器并终止程序...")
            else:
                print("任务完成，根据配置将自动关闭浏览器。")

    finally:
        print("\n程序即将终止，正在关闭浏览器...")
        driver.quit()


if __name__ == "__main__":
    main()
