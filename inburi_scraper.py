import requests
import json
import os
from datetime import datetime
import pytz

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

# --- การตั้งค่าสำหรับสคริปต์นี้โดยเฉพาะ ---
STATION_API_URL = "https://www.thaiwater.net/water/api/stations/tele_wl/C35"
LAST_DATA_FILE = 'last_inburi_data.txt'

def get_inburi_river_data():
    """ดึงข้อมูลระดับน้ำและระดับตลิ่งจาก API ของ ThaiWater.net สำหรับสถานี C.35"""
    try:
        print(f"Fetching data from ThaiWater API for station C35...")
        response = requests.get(STATION_API_URL, timeout=15)
        response.raise_for_status()

        try:
            api_data = response.json()
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON. The response from the server is not valid JSON.")
            print("--- Server Response Text (First 500 chars) ---")
            print(response.text[:500])
            print("---------------------------------------------")
            return None

        latest_data = api_data['data']['data'][-1]
        station_name_full = api_data['data']['station']['tele_station_name']
        water_level_str = latest_data['storage_water_level']
        bank_level_str = api_data['data']['station']['ground_level']

        print(f"Found station: {station_name_full}")
        print(f"  - Water Level: {water_level_str}")
        print(f"  - Bank Level: {bank_level_str}")

        if water_level_str is None or bank_level_str is None:
            print("Warning: Water level or bank level data is null.")
            return None

        water_level = float(water_level_str)
        bank_level = float(bank_level_str)
        overflow = water_level - bank_level

        return {
            "station": station_name_full,
            "water_level": water_level,
            "bank_level": bank_level,
            "overflow": overflow
        }

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        return None
    except (ValueError, IndexError, KeyError) as e:
        print(f"An error occurred while parsing the data: {e}")
        return None

def send_line_message(data):
    """ส่งข้อความแจ้งเตือนระดับน้ำของอินทร์บุรี"""
    now_thailand = datetime.now(TIMEZONE_THAILAND)
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M น.")

    if data['overflow'] > 0:
        status_text = "⚠️ *น้ำล้นตลิ่ง*"
        status_icon = "🚨"
        overflow_text = f"{data['overflow']:.2f} ม."
    else:
        status_text = "✅ *ระดับน้ำปกติ*"
        status_icon = "🌊"
        overflow_text = f"ต่ำกว่าตลิ่ง {-data['overflow']:.2f} ม."

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
        with open(file_path, 'r') as f:
            return f.read().strip()
    return ""

def write_data(file_path, data):
    with open(file_path, 'w') as f:
        f.write(data)

def main():
    """ตรรกะหลักของโปรแกรม"""
    current_data_dict = get_inburi_river_data()
    
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

# --- ส่วน "ปุ่มสตาร์ท" ที่สำคัญ ---
if __name__ == "__main__":
    main()
