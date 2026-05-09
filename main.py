# -*- coding: utf-8 -*-
from datetime import date, datetime
from email.utils import formataddr
import os
import random
import traceback
from dotenv import load_dotenv
load_dotenv()
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.header import Header

# --- 全局配置 ---
# 选择您要监控的领事馆: "SHANGHAI" / "WUHAN" / "SHENYANG"
LOCATION_NAME = "SHENYANG"

LOCATIONS = {
    "SHANGHAI": {"name": "SHANGHAI", "id": "096bf614-b0db-ec11-a7b4-001dd80234f6"},
    "WUHAN": {"name": "WUHAN", "id": "7b6af614-b0db-ec11-a7b4-001dd80234f6"},
    "SHENYANG": {"name": "SHENYANG", "id": "0f6bf614-b0db-ec11-a7b4-001dd80234f6"},
}
LOCATION_VALUE_ID = LOCATIONS[LOCATION_NAME]["id"]

# --- 自动预定配置 ---
BOOKING_CONFIG = {
    "BOOKING_ENABLED": False,
    "EARLIEST_DATE_STR": "2025-08-01",   # 可接受的最早预约日期
    "LATEST_DATE_STR": "2025-08-31",     # 可接受的最晚预约日期
    "DRY_RUN": True,                     # True=安全模式(不提交), False=真实预定
    "KEEP_BROWSER_OPEN_ON_EXIT": True    # 任务完成后是否保持浏览器打开
}

# 申请人姓名 (必须与预约系统中显示的完全一致，用于确认页面已正确加载)
APPLICANT_NAME = os.environ["APPLICANT_NAME"]

# 邮件配置 — 通过环境变量或 .env 文件设置
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVERS = [r.strip() for r in os.environ["EMAIL_RECEIVER"].split(",")]

# --- 邮件发送函数 ---
def send_notification_email(added_dates, removed_dates, all_dates):
    if not added_dates and not removed_dates: return
    subject = f"【签证监控】{LOCATION_NAME} F1签证日期变动！"
    body_lines = [f"领事馆: {LOCATION_NAME}"]
    if added_dates:
        body_lines.append("\n新增的可预约日期:")
        for d in sorted(added_dates): body_lines.append(f"  ✅ {d}")
    if removed_dates:
        body_lines.append("\n不再可用的日期:")
        for d in sorted(removed_dates): body_lines.append(f"  ❌ {d}")
    body_lines.append("\n\n当前所有可预约日期:")
    body_lines.append("\n".join([f"  - {d}" for d in sorted(all_dates)]) if all_dates else "  (暂无可用日期)")
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
        f"【签证监控】{LOCATION_NAME} 会话已过期，请重新登录",
        f"领事馆: {LOCATION_NAME}\n\n监控脚本检测到登录会话已过期，已暂停监控。\n请重新登录预约系统并在终端按 Enter 键继续。",
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
        # Strategy 1: SMTP_SSL on configured port (e.g. 465) with explicit context
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

        # Strategy 2: STARTTLS on port 587
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

        raise RuntimeError(f"所有连接方式均失败")

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

def countdown_timer(total_seconds):
    """在终端显示倒计时，单行刷新直到结束。"""
    print()
    while total_seconds > 0:
        mins, secs = divmod(total_seconds, 60)
        print(f'下一次检查将在 {mins:02d}:{secs:02d} 后开始...', end='\r')
        time.sleep(1)
        total_seconds -= 1
    print("\n倒计时结束。                                   ")

# --- 主程序 ---
def main():
    options = uc.ChromeOptions()
    for arg in ["--no-first-run", "--no-service-autorun", "--password-store=basic"]:
        options.add_argument(arg)
    driver = uc.Chrome(options=options)
    
    booking_completed_successfully = False

    try:
        wait = WebDriverWait(driver, 60)
        current_dates = set()
        
        # 动态等待配置
        SHORT_WAIT_MIN, SHORT_WAIT_MAX = 3, 5
        LONG_REST_MIN, LONG_REST_MAX = 7, 9
        checks_until_long_rest = random.randint(4, 7)
        last_status_email_time = time.time()
        checks_since_last_status = 0

        # 1. 手动登录
        driver.get("https://www.usvisascheduling.com/zh-CN/schedule/")
        print("="*50)
        print("页面已打开，请在浏览器中手动完成登录和二次验证。")
        print("重要提示：请确保您当前操作的申请是您的 F1 签证申请！")
        if BOOKING_CONFIG['BOOKING_ENABLED']:
            print("\n--- 自动预定已启用 ---")
            print(f"可接受日期范围: {BOOKING_CONFIG['EARLIEST_DATE_STR']} 至 {BOOKING_CONFIG['LATEST_DATE_STR']}")
            print(f"模式: {'安全模式 (Dry Run)' if BOOKING_CONFIG['DRY_RUN'] else '真实预定模式'}")
            print(f"结束时保持浏览器: {'是' if BOOKING_CONFIG['KEEP_BROWSER_OPEN_ON_EXIT'] else '否'}")
            print("------------------------")
        input("登录和验证完成后，请按 Enter 键继续运行脚本...")
        print("="*50)

        # 2. 循环监控
        while True:
            try:
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始新一轮检查...")
                driver.refresh()
                print("页面已刷新，等待页面加载...")

                # Dismiss any JS alert that the site may show after a refresh
                try:
                    alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                    print(f"检测到弹窗: \"{alert.text}\"，已自动关闭，稍后重试。")
                    alert.dismiss()
                    countdown_timer(60)
                    continue
                except TimeoutException:
                    pass

                # 等待并选择领事馆
                wait.until(EC.visibility_of_element_located((By.XPATH, f"//label[text()='{APPLICANT_NAME}']")))
                print("申请人加载成功，等待领事馆选择下拉框及其选项加载...")

                option_locator = (By.XPATH, f"//select[@id='post_select']/option[@value='{LOCATION_VALUE_ID}']")
                print("正在等待目标领事馆选项加载...")
                wait.until(EC.presence_of_element_located(option_locator))
                print("目标领事馆选项已成功加载。")

                select = Select(driver.find_element(By.ID, "post_select"))
                print(f"正在选择领事馆: {LOCATION_NAME}")
                select.select_by_value(LOCATION_VALUE_ID)
                
                print("领事馆选择成功，等待日历加载...")
                available_dates = set()
                try:
                    # Wait for "正在加载" to disappear from the page before reading results.
                    wait.until(lambda d: "正在加载" not in d.find_element(By.TAG_NAME, "body").text)
                    print("加载完成，正在读取结果...")

                    error_rows = driver.find_elements(By.ID, "error_row")
                    if error_rows and error_rows[0].is_displayed():
                        error_text = error_rows[0].text.strip()
                        if "无可用时段" in error_text:
                            print("当前无可用时段。")
                        else:
                            print(f"页面返回错误: {error_text}")
                    else:
                        day_cells = driver.find_elements(By.CSS_SELECTOR, "td[data-handler='selectDay'].greenday")
                        print(f"日历加载完成，发现 {len(day_cells)} 个可用日期。")
                        for cell in day_cells:
                            try:
                                day = cell.find_element(By.CSS_SELECTOR, "a.ui-state-default").text
                                month = int(cell.get_attribute("data-month")) + 1
                                year = int(cell.get_attribute("data-year"))
                                available_dates.add(date(year, month, int(day)).isoformat())
                            except Exception as e:
                                print(f"解析日期单元格时出错: {e}")
                except TimeoutException:
                    if "usvisascheduling.com" not in driver.current_url or "login" in driver.current_url.lower():
                        raise
                    print("等待加载超时，跳过本轮。")

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
                        
                        # 使用更精确的XPath定位器，它同时匹配年、月、日
                        target_cell_xpath = f"//td[@data-year='{year_to_click}' and @data-month='{month_to_click}']//a[text()='{day_to_click}']"
                        target_cell_link = wait.until(EC.element_to_be_clickable((By.XPATH, target_cell_xpath)))
                        print(f"步骤 1/4: 正在点击日期 {book_date_str}...")
                        target_cell_link.click()

                        print("步骤 2/4: 等待并选择时间...")
                        # 找到第一个radio按钮并点击
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

                checks_since_last_status += 1

                if not current_dates and time.time() - last_status_email_time >= 6 * 3600:
                    send_status_email(checks_since_last_status)
                    last_status_email_time = time.time()
                    checks_since_last_status = 0

                if not booking_completed_successfully:
                    checks_until_long_rest -= 1
                    if checks_until_long_rest <= 0:
                        rest_secs = random.randint(LONG_REST_MIN * 60, LONG_REST_MAX * 60)
                        print(f"\n--- 本轮检查完成，进入长时休眠 {rest_secs // 60}分{rest_secs % 60:02d}秒... ---")
                        countdown_timer(rest_secs)
                        checks_until_long_rest = random.randint(4, 7)
                    else:
                        wait_secs = random.randint(SHORT_WAIT_MIN * 60, SHORT_WAIT_MAX * 60)
                        print(f"\n--- 本轮检查完成，常规等待 {wait_secs // 60}分{wait_secs % 60:02d}秒... ---")
                        countdown_timer(wait_secs)

            except UnexpectedAlertPresentException as e:
                # Dismiss the alert before touching driver.current_url, which
                # would itself raise if the alert is still open.
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
                    print("检测到会话已过期或被重定向至登录页面，请重新手动登录后按 Enter 继续...")
                    send_relogin_email()
                    input()
                else:
                    print("将等待1分钟后重试。")
                    countdown_timer(60)
        
        if booking_completed_successfully:
            print("\n" + "="*50)
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