import requests
import os
import json
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

# --- การตั้งค่าสำหรับสคริปต์นี้โดยเฉพาะ ---
BASE_URL = "https://singburi.thaiwater.net/wl"
API_URL = "https://singburi.thaiwater.net/api/v1/tele_waterlevel"
LAST_DATA_FILE = 'last_inburi_data.txt'
STATION_ID_TO_FIND = "C.35"
NOTIFICATION_THRESHOLD_METERS = 0.20

def get_inburi_river_data():
    """
    ดึงข้อมูลโดยการเรียก API ของเว็บโดยตรง (วิธีที่เสถียรที่สุด)
    ขั้นตอน:
    1. สร้าง Session เพื่อจัดการคุกกี้อัตโนมัติ
    2. เข้าหน้าเว็บหลัก (BASE_URL) เพื่อรับ CSRF Token จาก meta tag
    3. นำ Token ที่ได้ไปใช้เป็น Header ในการเรียก API_URL
    """
    print("Fetching data via direct API call...")
    try:
        # 1. สร้าง Session เพื่อเก็บคุกกี้ระหว่าง requests
        session = requests.Session()
        
        # ตั้งค่า Header ให้เหมือนเบราว์เซอร์จริง
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }
        
        # 2. เข้าหน้าเว็บหลักเพื่อเอา CSRF Token
        print(f"Visiting {BASE_URL} to get CSRF token...")
        main_page_response = session.get(BASE_URL, headers=headers, timeout=20)
        main_page_response.raise_for_status()
        
        # ดึง Token จาก <meta> tag
        soup = BeautifulSoup(main_page_response.text, 'html.parser')
        token_tag = soup.find('meta', {'name': 'csrf-token'})
        
        if not token_tag or not token_tag.get('content'):
            print("Error: Could not find CSRF token on the main page.")
            return None
            
        csrf_token = token_tag.get('content')
        print(f"Successfully retrieved CSRF token.")

        # 3. เตรียม Header สำหรับยิง API
        api_headers = headers.copy()
        api_headers.update({
            'X-CSRF-TOKEN': csrf_token,
            'X-Requested-With': 'XMLHttpRequest', # บอก Server ว่าเป็นการเรียกข้อมูลเบื้องหลัง
            'Referer': BASE_URL # อ้างอิงว่าเรามาจากหน้าเว็บหลัก
        })
        
        # ยิง Request ไปที่ API
        print(f"Calling API at {API_URL}...")
        api_response = session.get(API_URL, headers=api_headers, timeout=20)
        api_response.raise_for_status()
        
        # 4. แปลงข้อมูล JSON และค้นหาสถานี
        all_stations_data = api_response.json()
        target_station_data = next((s for s in all_stations_data if s.get('id') == STATION_ID_TO_FIND), None)

        if not target_station_data:
            print(f"Could not find station {STATION_ID_TO_FIND} in the API response.")
            return None
        
        station_name = f"ต.{target_station_data.get('tumbon')} อ.{target_station_data.get('amphoe')}"
        water_level = float(target_station_data.get('level', 0))
        bank_level = float(target_station_data.get('bank', 0))
        overflow = water_level - bank_level
        
        print(f"Successfully found data for station: {station_name} (ID: {STATION_ID_TO_FIND})")
        print(f"  - Water Level: {water_level:.2f} m, Bank Level: {bank_level:.2f} m.")

        return {"station": station_name, "water_level": water_level, "bank_level": bank_level, "overflow": overflow}

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# ฟังก์ชันที่เหลือทั้งหมด (send_line_message, read_last_data, write_data, main) ให้ใช้ของเดิม ไม่ต้องแก้ไข
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
