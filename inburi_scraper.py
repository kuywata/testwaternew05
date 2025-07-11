import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import pytz
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

# --- การตั้งค่าสำหรับสคริปต์นี้โดยเฉพาะ ---
STATION_URL = "https://singburi.thaiwater.net/wl"
LAST_DATA_FILE = 'last_inburi_data.txt'
STATION_ID_TO_FIND = "C.35"

# --- เกณฑ์การแจ้งเตือน ---
NOTIFICATION_THRESHOLD_METERS = 0.20

def get_inburi_river_data():
    """ดึงข้อมูลระดับน้ำโดยใช้ Selenium + BeautifulSoup แบบยืดหยุ่น ไม่อิง ID ตายตัว"""
    print("Setting up Selenium Chrome driver...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # เปลี่ยนเป็น headless มาตรฐาน
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/98.0.4758.102 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(90)

    try:
        print(f"Fetching data from {STATION_URL} ...")
        driver.get(STATION_URL)

        # รอให้ JavaScript โหลดข้อมูล
        print("Page loaded. Pausing for 5 seconds to allow JS to render tables...")
        time.sleep(5)

        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')

        # หา table ทั้งหมด แล้ววนหา row ที่มีรหัสสถานี
        tables = soup.find_all('table')
        if not tables:
            print("No <table> elements found on the page.")
            return None

        target_row = None
        for table in tables:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if cols and STATION_ID_TO_FIND in cols[0].get_text():
                    target_row = cols
                    break
            if target_row:
                break

        if not target_row:
            print(f"Could not find station {STATION_ID_TO_FIND} in any table.")
            return None

        station_name = target_row[0].get_text(strip=True)
        # บางครั้งตัวเลขอาจมีคอมม่าให้ลบออกก่อนแปลง float
        water_level_str = target_row[2].get_text(strip=True).replace(',', '')
        bank_level_str = target_row[3].get_text(strip=True).replace(',', '')

        print(f"Found station: {station_name}")
        print(f"  - Water Level: {water_level_str} m.")
        print(f"  - Bank Level: {bank_level_str} m.")

        water_level = float(water_level_str)
        bank_level = float(bank_level_str)
        overflow = water_level - bank_level

        return {
            "station": station_name,
            "water_level": water_level,
            "bank_level": bank_level,
            "overflow": overflow
        }

    except Exception as e:
        print(f"An error occurred in get_inburi_river_data: {e}")
        return None
    finally:
        print("Closing Selenium driver.")
        driver.quit()

def send_line_message(data, change_amount):
    """ส่งข้อความไปยัง LINE พร้อมระบุการเปลี่ยนแปลง"""
    now_thailand = datetime.now(TIMEZONE_THAILAND)
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M น.")
    
    icon = "⬆️" if change_amount > 0 else "⬇️"
    change_text = f"เปลี่ยนแปลง {icon} {abs(change_amount):.2f} ม."
    
    if data['overflow'] > 0:
        status_text, status_icon, overflow_text = "⚠️ *น้ำล้นตลิ่ง*", "🚨", f"{data['overflow']:.2f} ม."
    else:
        status_text, status_icon, overflow_text = "✅ *ระดับน้ำปกติ*", "🌊", f"ต่ำกว่าตลิ่ง {-data['overflow']:.2f} ม."

    message = (
        f"{status_icon} *แจ้งเตือนระดับน้ำแม่น้ำเจ้าพระยา*\n"
        f"📍 *พื้นที่: {data['station']}*\n"
        f"━━━━━━━━━━━━━━\n"
        f"💧 *ระดับน้ำปัจจุบัน:* {data['water_level']:.2f} ม. (รทก.)\n"
        f"({change_text})\n"
        f"🏞️ *ระดับขอบตลิ่ง:* {data['bank_level']:.2f} ม. (รทก.)\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 *สถานะ:* {status_text}\n"
        f"({overflow_text})\n\n"
        f"🗓️ {formatted_datetime}"
    )

    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        print("LINE message for In Buri sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending LINE message: {e.response.text if e.response else e}")

def read_last_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                return float(f.read().strip())
            except (ValueError, TypeError):
                return None
    return None

def write_data(file_path, data):
    with open(file_path, 'w') as f:
        f.write(str(data))

def main():
    current = get_inburi_river_data()
    if current is None:
        print("Could not retrieve current data. Exiting.")
        return

    last = read_last_data(LAST_DATA_FILE)
    print(f"Current water level: {current['water_level']:.2f} m.")
    print(f"Last recorded level: {last if last is not None else 'N/A'}")

    notify = False
    diff = 0.0
    if last is None:
        print("No last data found. Sending initial notification.")
        notify = True
    else:
        diff = current['water_level'] - last
        if abs(diff) >= NOTIFICATION_THRESHOLD_METERS:
            print(f"Change of {abs(diff):.2f} m meets threshold.")
            notify = True
        else:
            print(f"Change of {abs(diff):.2f} m below threshold. No notify.")

    if notify:
        send_line_message(current, diff)

    print(f"Saving current level ({current['water_level']:.2f}) to {LAST_DATA_FILE}.")
    write_data(LAST_DATA_FILE, current['water_level'])

if __name__ == "__main__":
    main()
