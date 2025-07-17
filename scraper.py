import os
import time
import re
import requests
from datetime import datetime, timedelta
import pytz
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ‑‑‑ ค่าคงที่และ URL ‑‑‑
URL = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')
HISTORICAL_LOG_FILE = 'historical_log.csv'
LAST_DATA_FILE = 'last_data.txt'


def get_water_data():
    """
    เปิดหน้าเว็บด้วย Selenium แบบ headless ให้ JS ทำงานก่อน
    แล้ว parse เอา <td class="text_bold" colspan="2"> ที่มีค่า “439.00/… cms”
    คืนค่า "439.00 cms" หรือตัวเลข+หน่วย หากเจอ
    """
    # เซ็ต Chrome headless
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    driver.get(URL)
    time.sleep(5)  # รอให้ JS โหลดข้อมูลเสร็จ
    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, 'html.parser')
    # เลือก td ที่คุณระบุ (within <tr valign="buttom"> แต่ selector นี้ก็เพียงพอ)
    cell = soup.select_one('td.text_bold[colspan="2"]')
    if cell:
        txt = cell.get_text(strip=True)  # e.g. "439.00/2840cms"
        # ตัดเอาส่วนก่อน "/" แล้วลบตัวอักษรที่ไม่ใช่ตัวเลขหรือจุดออก
        main = txt.split('/', 1)[0]
        clean = re.sub(r'[^\d.]', '', main)
        if clean:
            return f"{clean} cms"

    # ถ้าไม่เจอ fallback ด้วย regex หาเลข+cms ใดๆ ใน html
    m = re.search(r'([\d\.]+)\s*cms', html)
    if m:
        return f"{m.group(1)} cms"

    print("Error: ไม่พบข้อมูลปริมาณน้ำ")
    return None


def get_historical_data(target_date):
    if not os.path.exists(HISTORICAL_LOG_FILE):
        return None
    start = target_date - timedelta(hours=12)
    end = target_date + timedelta(hours=12)
    best, best_diff = None, timedelta.max
    with open(HISTORICAL_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                ts, val = line.strip().split(',', 1)
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = TIMEZONE_THAILAND.localize(dt)
                if start <= dt <= end:
                    diff = abs(target_date - dt)
                    if diff < best_diff:
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
    # อ่านค่าก่อนหน้า
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
    last_year = now_th - timedelta(days=365)
    hist = get_historical_data(last_year)
    hist_str = f"\n\nเทียบกับปีที่แล้ว ({last_year.strftime('%d/%m/%Y')}): {hist}" if hist else ''

    message = (
        f"🌊 แจ้งเตือนปล่อยน้ำ เขื่อนเจ้าพระยา\n"
        f"━━━━━━━━━━\n"
        f"✅ ค่าปัจจุบัน: {current}\n"
        f"⬅️ ค่าเดิม: {last or 'ไม่พบ'}\n"
        f"🗓️ {now_th.strftime('%d/%m/%Y %H:%M:%S')}"
        f"{hist_str}"
    )
    send_line_message(message)

    # บันทึกข้อมูล
    with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(current)
    append_to_historical_log(now_th, current)
    print("อัปเดต historical log เรียบร้อย")


if __name__ == "__main__":
    main()
