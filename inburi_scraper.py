import requests
import os
import json
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# เพิ่ม import ที่จำเป็นสำหรับ Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

# --- การตั้งค่าสำหรับสคริปต์นี้โดยเฉพาะ ---
STATION_URL = "https://singburi.thaiwater.net/wl"
LAST_DATA_FILE = 'last_inburi_data.txt'
STATION_ID_TO_FIND = "C.35"
NOTIFICATION_THRESHOLD_METERS = 0.20

def get_inburi_river_data():
    """
    ดึงข้อมูลโดยใช้ Selenium และรอจนกว่า 'ตารางข้อมูล' จะแสดงผล
    ซึ่งเป็นวิธีที่เสถียรกว่าการรอ JavaScript variable โดยตรง
    """
    print("Initializing Selenium WebDriver...")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = None 
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        wait_timeout = 60  # เพิ่มเวลารอเป็น 60 วินาที
        
        print(f"Navigating to {STATION_URL}...")
        driver.get(STATION_URL)
        print(f"Page title is: '{driver.title}'")

        # --- ส่วนที่แก้ไข ---
        # เปลี่ยนจากการรอตัวแปร JavaScript เป็นการรอให้ 'แถวแรกของตารางข้อมูล' ปรากฏขึ้น
        print(f"Waiting for up to {wait_timeout} seconds for the data table (#wl-table) to be populated...")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#wl-table tbody tr"))
        )
        # --------------------
        
        print("Data table is present. Parsing data...")
        html_content = driver.page_source
        
        soup = BeautifulSoup(html_content, 'html.parser')
        scripts = soup.find_all('script')
        
        json_data_string = None
        for script in scripts:
            if script.string and 'var tele_data_wl' in script.string:
                text = script.string
                start = text.find('[')
                end = text.rfind(']') + 1
                json_data_string = text[start:end]
                break
        
        if not json_data_string:
            print("Could not find JavaScript variable 'tele_data_wl' even after the table appeared.")
            return None

        all_stations_data = json.loads(json_data_string)
        target_station_data = next((s for s in all_stations_data if s.get('id') == STATION_ID_TO_FIND), None)
        
        if not target_station_data:
            print(f"Could not find station {STATION_ID_TO_FIND} in the parsed data.")
            return None

        station_name = f"ต.{target_station_data.get('tumbon')} อ.{target_station_data.get('amphoe')}"
        water_level = float(target_station_data.get('level', 0))
        bank_level = float(target_station_data.get('bank', 0))
        overflow = water_level - bank_level
        
        print(f"Successfully found data for station: {station_name} (ID: {STATION_ID_TO_FIND})")
        print(f"  - Water Level: {water_level:.2f} m, Bank Level: {bank_level:.2f} m.")

        return {"station": station_name, "water_level": water_level, "bank_level": bank_level, "overflow": overflow}

    except TimeoutException:
        print(f"Error: Timed out after {wait_timeout} seconds waiting for the data table to appear.")
        if driver:
            print("Page source at the time of timeout (first 2000 chars):")
            print(driver.page_source[:2000]) 
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Selenium process: {e}")
        return None
    finally:
        if driver:
            print("Closing WebDriver.")
            driver.quit()

def send_line_message(data, change_amount):
    now_thailand = datetime.now(TIMEZONE_THAILAND)
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M น.")
    
    last_level = read_last_data(LAST_DATA_FILE)

    if last_level is None:
        change_text = "รายงานข้อมูลครั้งแรก"
    elif change_amount == 0.0:
        change_text = "ระดับน้ำไม่เปลี่ยนแปลง"
    else:
        change_direction_icon = "⬆️" if change_amount > 0 else "⬇️"
        change_text = f"เปลี่ยนแปลง {change_direction_icon} {abs(change_amount):.2f} ม."
    
    if data['overflow'] > 0:
        status_text, status_icon, overflow_text = "⚠️ *น้ำล้นตลิ่ง*", "🚨", f"{data['overflow']:.2f} ม."
    else:
        status_text, status_icon, overflow_text = "✅ *ระดับน้ำปกติ*", "🌊", f"ต่ำกว่าตลิ่ง {-data['overflow']:.2f} ม."

    message = (
        f"{status_icon} *แจ้งเตือนระดับน้ำแม่น้ำเจ้าพระยา*\n"
        f"📍 *พื้นที่: สถานีอินทร์บุรี ({data['station']})*\n"
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
                return None
    return None

def write_data(file_path, data):
    with open(file_path, 'w') as f:
        f.write(str(data))

def main():
    current_data_dict = get_inburi_river_data()
    if current_data_dict is None:
        print("Could not retrieve current data. Exiting.")
        return

    current_level = current_data_dict['water_level']
    last_level = read_last_data(LAST_DATA_FILE)

    print(f"Current water level: {current_level:.2f} m.")
    print(f"Last recorded level: {last_level if last_level is not None else 'N/A'}")

    should_notify = False
    change_diff = 0.0

    if last_level is None:
        print("No last data found. Sending initial notification.")
        should_notify = True
    else:
        change_diff = current_level - last_level
        if abs(change_diff) >= NOTIFICATION_THRESHOLD_METERS:
            print(f"Change of {abs(change_diff):.2f}m detected, which meets or exceeds the threshold.")
            should_notify = True
        else:
            print(f"Change of {abs(change_diff):.2f}m is less than the threshold. No notification needed.")
    
    if should_notify:
        send_line_message(current_data_dict, change_diff)
        print(f"Saving current level ({current_level:.2f}) to {LAST_DATA_FILE}.")
        write_data(LAST_DATA_FILE, current_level)
    else:
        print("No notification sent, not updating the last data file.")

if __name__ == "__main__":
    main()
