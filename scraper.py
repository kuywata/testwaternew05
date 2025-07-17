import os
import re
import requests
from datetime import datetime, timedelta
import pytz

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── ค่าคงที่ ──────────────────────────────────────────────────────
URL = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID             = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND          = pytz.timezone('Asia/Bangkok')
HISTORICAL_LOG_FILE        = 'historical_log.csv'
LAST_DATA_FILE             = 'last_data.txt'


def get_water_data(timeout=15):
    """  
    เปิดหน้าเว็บแบบ headless, รอให้ td.text_bold[colspan="2"] ปรากฏ,
    ดึงข้อความ เช่น "439.00/ 2840 cms" แล้ว return "439.00 cms"
    """
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    driver.get(URL)

    try:
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'td.text_bold[colspan="2"]')))
        elem = driver.find_element(By.CSS_SELECTOR, 'td.text_bold[colspan="2"]')
        raw = elem.text          # ex: "439.00/ 2840 cms"
    except Exception as e:
        print("Selenium error or timeout:", e)
        raw = driver.page_source  # fallback ไป regex
    finally:
        driver.quit()

    # ถ้า raw เป็นข้อความ `<td>` ให้แยกก่อน slash
    if "/" in raw:
        main = raw.split("/", 1)[0]
        num  = re.sub(r"[^\d.]", "", main)
        if num:
            return f"{num} cms"

    # fallback: หาเลข+cms ใน raw ทั้งหน้า
    m = re.search(r"([\d\.]+)\s*cms", raw)
    if m:
        return f"{m.group(1)} cms"

    print("Error: ไม่พบข้อมูลปริมาณน้ำ")
    return None


def get_historical_data(target_date):
    if not os.path.exists(HISTORICAL_LOG_FILE):
        return None
    start = target_date - timedelta(hours=12)
    end   = target_date + timedelta(hours=12)
    best, best_diff = None, timedelta.max
    with open(HISTORICAL_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                ts, val = line.strip().split(",", 1)
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = TIMEZONE_THAILAND.localize(dt)
                diff = abs(target_date - dt)
                if start <= dt <= end and diff < best_diff:
                    best_diff, best = diff, val
            except ValueError:
                continue
    return best


def append_to_historical_log(now, data):
    with open(HISTORICAL_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{now.isoformat()},{data}\n")


def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("Missing LINE credentials.")
        return
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {
        'to': LINE_TARGET_ID,
        'messages': [{'type': 'text', 'text': message}]
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        print("ส่งข้อความ LINE สำเร็จ:", resp.status_code)
    except Exception as e:
        print("ส่งข้อความ LINE ไม่สำเร็จ:", e)


def main():
    # อ่านค่าปัจจุบันและค่าเก่า
    last = ''
    if os.path.exists(LAST_DATA_FILE):
        last = open(LAST_DATA_FILE, 'r', encoding='utf-8').read().strip()

    current = get_water_data()
    if not current:
        print("ไม่สามารถดึงค่าปัจจุบันได้ จึงไม่มีการแจ้งเตือน")
        return

    print("ค่าปัจจุบัน:", current)
    now_th = datetime.now(TIMEZONE_THAILAND)

    # หาเทียบกับปีที่แล้ว
    hist = get_historical_data(now_th - timedelta(days=365))
    hist_str = f"\n\nเทียบปีที่แล้ว ({(now_th - timedelta(days=365)).strftime('%d/%m/%Y')}): {hist}" if hist else ''

    msg = (
        f"🌊 แจ้งเตือนปริมาณน้ำ เขื่อนเจ้าพระยา\n"
        f"━━━━━━━━━━\n"
        f"✅ ปัจจุบัน: {current}\n"
        f"⬅️ เดิม: {last or 'ไม่พบ'}\n"
        f"🗓️ {now_th.strftime('%d/%m/%Y %H:%M:%S')}"
        f"{hist_str}"
    )
    send_line_message(msg)

    # อัปเดตไฟล์เก็บข้อมูล
    with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(current)
    append_to_historical_log(now_th, current)
    print("อัปเดต historical log เรียบร้อย")


if __name__ == "__main__":
    main()
