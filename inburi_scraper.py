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
STATION_URL = "https://singburi.thaiwater.net/wl" # กลับมาใช้ URL ของหน้าเว็บหลัก
LAST_DATA_FILE = 'last_inburi_data.txt'
STATION_ID_TO_FIND = "C.35"
NOTIFICATION_THRESHOLD_METERS = 0.20

def get_inburi_river_data():
    """
    ดึงข้อมูลโดยการอ่านหน้า HTML แล้วสกัดเอา JSON ที่ซ่อนอยู่ใน <script>
    วิธีนี้ไม่ต้องใช้ Selenium และแก้ปัญหา API ที่เรียกตรงๆ ไม่ได้
    """
    print("Fetching data directly from HTML and parsing JavaScript...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(STATION_URL, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script')
        
        json_data_string = None
        for script in scripts:
            if script.string and 'var tele_data_wl' in script.string:
                # เจอ Script ที่มีข้อมูล เราจะตัดเอาเฉพาะส่วนที่เป็น JSON
                text = script.string
                start = text.find('[')
                end = text.rfind(']') + 1
                json_data_string = text[start:end]
                break
        
        if not json_data_string:
            print("Could not find JavaScript variable 'tele_data_wl' in the page.")
            return None

        all_stations_data = json.loads(json_data_string)
        
        target_station_data = None
        for station in all_stations_data:
            if station.get('id') == STATION_ID_TO_FIND:
                target_station_data = station
                break
        
        if not target_station_data:
            print(f"Could not find station {STATION_ID_TO_FIND} in the parsed data.")
            return None

        station_name = f"ต.{target_station_data.get('tumbon')} อ.{target_station_data.get('amphoe')}"
        water_level = float(target_station_data.get('level', 0))
        bank_level = float(target_station_data.get('bank', 0))
        
        print(f"Found station: {station_name} (ID: {STATION_ID_TO_FIND})")
        print(f"  - Water Level: {water_level:.2f} m.")
        print(f"  - Bank Level: {bank_level:.2f} m.")
        
        overflow = water_level - bank_level

        return {
            "station": station_name,
            "water_level": water_level,
            "bank_level": bank_level,
            "overflow": overflow
        }

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching HTML: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def send_line_message(data, change_amount):
    """ส่งข้อความไปยัง LINE พร้อมระบุการเปลี่ยนแปลง"""
    now_thailand = datetime.now(TIMEZONE_THAILAND)
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M น.")
    
    # สำหรับการแจ้งเตือนครั้งแรก ไม่ต้องแสดงการเปลี่ยนแปลง
    if change_amount == 0.0:
        change_text = "รายงานข้อมูลครั้งแรก"
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
        change_diff = 0.0
    else:
        change_diff = current_level - last_level
        if abs(change_diff) >= NOTIFICATION_THRESHOLD_METERS:
            print(f"Change of {abs(change_diff):.2f}m detected, which meets or exceeds the threshold of {NOTIFICATION_THRESHOLD_METERS}m.")
            should_notify = True
        else:
            print(f"Change of {abs(change_diff):.2f}m is less than the threshold. No notification needed.")
    
    if should_notify:
        send_line_message(current_data_dict, change_diff)
    
    print(f"Saving current level ({current_level:.2f}) to {LAST_DATA_FILE}.")
    write_data(LAST_DATA_FILE, current_level)


if __name__ == "__main__":
    main()
