import requests
import os
from datetime import datetime
import pytz

# --- 🎯 การตั้งค่าทั้งหมด ---
# URL ของ API ที่ดึงข้อมูลตารางโดยตรง
API_URL = "https://tiwrmdev.hii.or.th/v3/api/public/wl/warning" 
STATION_NAME_TO_FIND = "อินทร์บุรี" # ใช้ชื่อสถานีในการค้นหา
LAST_DATA_FILE = 'last_inburi_data.txt'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')
# --- จบส่วนการตั้งค่า ---

def get_inburi_river_data_from_api():
    """ดึงข้อมูลระดับน้ำโดยตรงจาก API"""
    print(f"Fetching data from API: {API_URL}")
    try:
        # ยิง request ไปที่ API และตั้ง timeout 30 วินาที
        response = requests.get(API_URL, timeout=30)
        # ตรวจสอบว่า request สำเร็จหรือไม่ (status code 200)
        response.raise_for_status() 
        
        # แปลงข้อมูล JSON ที่ได้มาเป็น Dictionary ของ Python
        api_data = response.json()
        print("Successfully fetched and parsed API data.")

        # ค้นหาสถานี "อินทร์บุรี" จากข้อมูลทั้งหมด
        target_station_data = None
        # api_data['data'] คือ list ของสถานีทั้งหมด
        for station in api_data.get('data', []): 
            # station['station']['station_name']['th'] คือชื่อสถานีภาษาไทย
            if STATION_NAME_TO_FIND in station.get('station', {}).get('station_name', {}).get('th', ''):
                target_station_data = station
                break # เจอแล้วให้หยุด loop

        if not target_station_data:
            print(f"Could not find station '{STATION_NAME_TO_FIND}' in the API response.")
            return None

        # ดึงข้อมูลที่ต้องการจาก Dictionary
        station_name_th = target_station_data['station']['station_name']['th']
        water_level = target_station_data['wl_tele']['storage_level']
        bank_level = target_station_data['station']['ground_level']
        overflow = water_level - bank_level if water_level and bank_level else 0
        
        print(f"Found station: {station_name_th}")
        print(f"  - Water Level: {water_level} m.")
        print(f"  - Bank Level: {bank_level} m.")

        return {
            "station": station_name_th,
            "water_level": float(water_level),
            "bank_level": float(bank_level),
            "overflow": overflow
        }

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while calling the API: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Data structure from API might have changed. Error: {e}")
        return None

def send_line_message(data):
    """ส่งข้อความแจ้งเตือนผ่าน LINE (โค้ดส่วนนี้เหมือนเดิม)"""
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
    if os.path.exists(file_path):
        with open(file_path, 'r') as f: return f.read().strip()
    return ""

def write_data(file_path, data):
    with open(file_path, 'w') as f: f.write(data)

def main():
    """ฟังก์ชันหลักในการทำงาน"""
    # เรียกใช้ฟังก์ชันใหม่ที่ดึงจาก API
    current_data_dict = get_inburi_river_data_from_api()
    if current_data_dict is None:
        print("Could not retrieve current data. Exiting.")
        return
        
    current_data_str = f"{current_data_dict['water_level']:.2f}"
    last_data_str = read_last_data(LAST_DATA_FILE)
    
    print(f"Current data string: {current_data_str}")
    print(f"Last data string: {last_data_str}")
    
    if current_data_str != last_data_str:
        print("Data has changed! Processing notification...")
        send_line_message(current_data_dict)
        write_data(LAST_DATA_FILE, current_data_str)
    else:
        print("Data has not changed. No action needed.")

if __name__ == "__main__":
    main()
