import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import pytz
import time
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- การตั้งค่าทั้งหมด ---
STATION_URL = "https://singburi.thaiwater.net/wl"
LAST_DATA_FILE = 'last_inburi_data.txt'
STATION_ID_TO_FIND = "C.35"
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

def get_inburi_river_data():
    """ดึงข้อมูลระดับน้ำโดยใช้ Selenium เพื่อรอ JavaScript โหลดข้อมูล"""
    print("Setting up Selenium Chrome driver...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"Fetching data from {STATION_URL}...")
        driver.get(STATION_URL)

        print("Waiting for data table to be loaded by JavaScript...")
        # --- 🎯 ส่วนที่แก้ไข 1: เพิ่มเวลารอเป็น 60 วินาที ---
        wait = WebDriverWait(driver, 60)
        table_element = wait.until(EC.presence_of_element_located((By.ID, 'tele_wl')))
        
        print("Table found! Parsing data...")
        # (ส่วนที่เหลือของ try block เหมือนเดิม)
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
        
        # --- 🎯 ส่วนที่แก้ไข 2: เพิ่มการสร้างไฟล์ Debug ---
        print("Saving debug files...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f'debug_screenshot_{timestamp}.png'
        pagesource_path = f'debug_page_source_{timestamp}.html'
        
        driver.save_screenshot(screenshot_path)
        with open(pagesource_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
            
        print(f"Saved screenshot to: {screenshot_path}")
        print(f"Saved page source to: {pagesource_path}")
        # --- จบส่วนแก้ไข ---
        
        traceback.print_exc()
        return None
    finally:
        print("Closing Selenium driver.")
        driver.quit()

# ... ส่วนที่เหลือของไฟล์ (send_line_message, main, etc.) ไม่ต้องแก้ไข ...
def send_line_message(data):
    """ส่งข้อความแจ้งเตือนผ่าน LINE"""
    now_thailand = datetime.now(TIMEZONE_THAILAND)
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M น.")
    
    if data['overflow'] > 0:
        status_text, status_icon, overflow_text = "⚠️ *น้ำล้นตลิ่ง*", "🚨", f"{data['overflow']:.2f} ม."
    else:
        status_text, status_icon, overflow_text = "✅ *ระดับน้ำปกติ*", "🌊", f"ต่ำกว่าตลิ่ง {-data['overflow']:.2f} ม."
        
    message = (
        f"{status_icon} *แจ้งเตือนระดับน้ำแม่น้ำเจ้าพระยา*\n"
        f"📍 *พื้นที่: {data['station']}*\n"
        f"━━━━━━━━━━━━━━\n"
        f"💧 *ระดับน้ำปัจจุบัน:* {data['water_level']:.2f} ม. (รทก.)\n"
        f"🏞️ *ระดับขอบตลิ่ง:* {data['bank_level']:.2f} ม. (รทก.)\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 *สถานะ:* {status_text}\n"
        f"({overflow_text})\n\n"
        f"🗓️ {formatted_datetime}"
    )
    
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
    """อ่านข้อมูลล่าสุดจากไฟล์"""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f: return f.read().strip()
    return ""


def write_data(file_path, data):
    """เขียนข้อมูลลงไฟล์"""
    with open(file_path, 'w') as f: f.write(data)


def main():
    """ฟังก์ชันหลักในการทำงาน"""
    current_data_dict = get_inburi_river_data()
    if current_data_dict is None:
        print("Could not retrieve current data. Exiting.")
        return
        
    current_data_str = f"{current_data_dict['water_level']:.2f}"
    last_data_str = read_last_data(LAST_DATA_FILE)
    
    if current_data_str != last_data_str:
        print("Data has changed! Processing notification...")
        send_line_message(current_data_dict)
        write_data(LAST_DATA_FILE, current_data_str)
    else:
        print("Data has not changed. No action needed.")


if __name__ == "__main__":
    main()
