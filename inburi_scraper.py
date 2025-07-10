import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import pytz
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

# --- การตั้งค่าสำหรับสคริปต์นี้โดยเฉพาะ ---
STATION_URL = "https://singburi.thaiwater.net/wl"
LAST_DATA_FILE = 'last_inburi_data.txt'
STATION_ID_TO_FIND = "C.35"

# --- 🎯 ส่วนที่แก้ไข: ตั้งค่าเกณฑ์การแจ้งเตือน ---
# ระบบจะแจ้งเตือนก็ต่อเมื่อระดับน้ำเปลี่ยนแปลงไปมากกว่าหรือเท่ากับค่านี้ (หน่วยเป็นเมตร)
# ตัวอย่าง: 0.20 = 20 เซนติเมตร
NOTIFICATION_THRESHOLD_METERS = 0.20

def get_inburi_river_data():
    """ดึงข้อมูลระดับน้ำโดยใช้ Selenium เพื่อรอ JavaScript โหลดข้อมูล"""
    print("Setting up Selenium Chrome driver with robust options for GitHub Actions...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    service = ChromeService()
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"Fetching data from {STATION_URL} with Selenium...")
        driver.get(STATION_URL)

        print("Waiting for data table to be loaded by JavaScript...")
        wait = WebDriverWait(driver, 30)
        table_element = wait.until(EC.presence_of_element_located((By.ID, 'tele_wl')))
        
        print("Table found! Parsing data...")
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')

        table = soup.find('table', id='tele_wl')
        if not table:
            print("Something went wrong, table with id 'tele_wl' not found.")
            return None

        target_row = None
        for row in table.find('tbody').find_all('tr'):
            columns = row.find_all('td')
            if columns and STATION_ID_TO_FIND in columns[0].text:
                target_row = columns
                break
        
        if not target_row:
            print(f"Could not find station {STATION_ID_TO_FIND} in the table.")
            return None

        station_name = target_row[0].text.strip()
        water_level_str = target_row[2].text.strip()
        bank_level_str = target_row[3].text.strip()

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
    
    # --- 🎯 ส่วนที่แก้ไข: เพิ่มข้อมูลการเปลี่ยนแปลงลงในข้อความ ---
    change_direction_icon = "⬆️" if change_amount > 0 else "⬇️"
    change_text = f"เปลี่ยนแปลง {change_direction_icon} {abs(change_amount):.2f} ม."
    
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
    # --- จบส่วนที่แก้ไข ---

    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    payload = {'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("LINE message for In Buri sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending LINE message: {e.response.text if e.response else 'No response'}")

def read_last_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                return float(f.read().strip())
            except (ValueError, TypeError):
                return None # หากไฟล์มีข้อมูลที่ไม่ใช่ตัวเลข
    return None

def write_data(file_path, data):
    with open(file_path, 'w') as f:
        f.write(str(data))

def main():
    """ตรรกะหลักของโปรแกรม"""
    current_data_dict = get_inburi_river_data()
    if current_data_dict is None:
        print("Could not retrieve current data. Exiting.")
        return

    current_level = current_data_dict['water_level']
    last_level = read_last_data(LAST_DATA_FILE)

    print(f"Current water level: {current_level:.2f} m.")
    print(f"Last recorded level: {last_level if last_level is not None else 'N/A'}")

    # --- 🎯 ส่วนที่แก้ไข: ตรรกะการเปรียบเทียบใหม่ทั้งหมด ---
    should_notify = False
    change_diff = 0.0

    if last_level is None:
        # ถ้าไม่มีข้อมูลเก่า (รันครั้งแรก) ให้แจ้งเตือนและบันทึกข้อมูลเลย
        print("No last data found. Sending initial notification.")
        should_notify = True
        change_diff = 0.0 # ไม่มีการเปลี่ยนแปลงสำหรับการแจ้งเตือนครั้งแรก
    else:
        # คำนวณส่วนต่างของระดับน้ำ
        change_diff = current_level - last_level
        # ตรวจสอบว่าส่วนต่าง 'มากกว่าหรือเท่ากับ' เกณฑ์ที่ตั้งไว้หรือไม่
        if abs(change_diff) >= NOTIFICATION_THRESHOLD_METERS:
            print(f"Change of {abs(change_diff):.2f}m detected, which meets or exceeds the threshold of {NOTIFICATION_THRESHOLD_METERS}m.")
            should_notify = True
        else:
            print(f"Change of {abs(change_diff):.2f}m is less than the threshold. No notification needed.")
    
    if should_notify:
        send_line_message(current_data_dict, change_diff)

    # บันทึกข้อมูลล่าสุดลงไฟล์ 'ทุกครั้ง' ที่รันสำเร็จ เพื่อให้การเปรียบเทียบครั้งต่อไปถูกต้องเสมอ
    print(f"Saving current level ({current_level:.2f}) to {LAST_DATA_FILE}.")
    write_data(LAST_DATA_FILE, current_level)
    # --- จบส่วนที่แก้ไข ---

if __name__ == "__main__":
    main()
