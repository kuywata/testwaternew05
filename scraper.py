import os
import time
import json
import requests
from datetime import datetime, timedelta
import pytz
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- ค่าคงที่และ URL ---
URL = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')
HISTORICAL_LOG_FILE = 'historical_log.csv'
LAST_DATA_FILE = 'last_data.txt'


def get_water_data():
    """
    ใช้ Selenium เปิดหน้าเว็บแบบ headless ให้ JS ทำงานก่อน แล้ว parse ผลลัพธ์
    คืนค่า "<number> cms" หรือ None ถ้ายังหาไม่เจอ
    """
    # ตั้งค่า Chrome options
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # เรียก Chrome ผ่าน Selenium
    driver = webdriver.Chrome(options=options)
    driver.get(URL)
    # รอให้ JS โหลดข้อมูลลง DOM
    time.sleep(5)

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, 'html.parser')

    # หา <td class="text_bold" colspan="2"> ที่น่าจะเป็นช่องปริมาณน้ำ
    tags = soup.find_all('td', class_='text_bold', colspan='2')
    for tag in tags:
        text = tag.get_text(strip=True)
        # คาดว่าข้อความเช่น "5.47 / 1,200.00 cms" 
        if '/' in text and 'cms' in text:
            # ตัดเอาส่วนก่อน "/" แล้ว strip
            value = text.split('/')[0].strip()
            # เติมหน่วย
            return f"{value} cms"

    # ถ้ายังไม่เจอ ลอง fallback ด้วย regex หาเลข + "cms" ใน source
    import re
    m = re.search(r'([\d\.]+)\s*cms', html)
    if m:
        return f"{m.group(1)} cms"

    print("Error: ไม่พบข้อมูลปริมาณน้ำหลังรัน JS แล้ว")
    return None


def get_historical_data(target_date):
    if not os.path.exists(HISTORICAL_LOG_FILE):
        return None
    start = target_date - timedelta(hours=12)
    end = target_date + timedelta(hours=12)
    best = None
    best_diff = timedelta.max
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
    last_data = ''
    if os.path.exists(LAST_DATA_FILE):
        with open(LAST_DATA_FILE, 'r', encoding='utf-8') as f:
            last_data = f.read().strip()

    current_data = get_water_data()
    if not current_data:
        print("ไม่สามารถดึงค่าปัจจุบันได้ จึงไม่มีการแจ้งเตือน")
        return

    print("ค่าปัจจุบัน:", current_data)
    now_th = datetime.now(TIMEZONE_THAILAND)

    # หาค่าเปรียบเทียบจากปีที่แล้ว
    last_year = now_th - timedelta(days=365)
    hist = get_historical_data(last_year)
    hist_text = ''
    if hist:
        hist_date_str = last_year.strftime("%d/%m/%Y")
        hist_text = f"\n\nเทียบกับปีที่แล้ว ({hist_date_str}): {hist}"

    dt_str = now_th.strftime("%d/%m/%Y %H:%M:%S")
    sponsor = "พื้นที่ผู้สนับสนุน..."

    message = (
        f"🌊 *แจ้งเตือนการปล่อยน้ำ เขื่อนเจ้าพระยา, ชัยนาท*\n"
        f"━━━━━━━━━━\n"
        f"✅ *ค่าปัจจุบัน:*\n{current_data}\n\n"
        f"⬅️ *ค่าเดิม (ก่อนหน้า):* {last_data if last_data else 'ไม่พบข้อมูลเดิม'}\n"
        f"━━━━━━━━━━\n"
        f"🗓️ {dt_str}"
        f"{hist_text}\n\n"
        f"{sponsor}"
    )

    send_line_message(message)

    # บันทึกข้อมูลปัจจุบัน
    with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(current_data)
    append_to_historical_log(now_th, current_data)
    print("อัปเดต historical log เรียบร้อย")


if __name__ == "__main__":
    main()
