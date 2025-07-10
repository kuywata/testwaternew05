import requests
import os
from datetime import datetime
import pytz

# --- 🎯 การตั้งค่าทั้งหมด ---
API_BASE = "https://tiwrmdev.hii.or.th"
API_VERSIONS = ["v3", "v2"]
STATION_NAME_TO_FIND = "อินทร์บุรี"  # ใช้ชื่อสถานีในการค้นหา
LAST_DATA_FILE = 'last_inburi_data.txt'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')
# --- จบส่วนการตั้งค่า ---

def get_inburi_river_data_from_api():
    """ดึงข้อมูลระดับน้ำโดยตรงจาก API และ fallback ระหว่างเวอร์ชัน"""
    api_data = None
    for ver in API_VERSIONS:
        url = f"{API_BASE}/{ver}/api/public/wl/warning"
        print(f"Trying API URL: {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            api_data = response.json()
            print(f"Successfully fetched from version {ver}")
            break
        except requests.HTTPError:
            print(f"Version {ver} returned status {response.status_code}, trying next")
        except requests.RequestException as e:
            print(f"Error fetching version {ver}: {e}, trying next")
    if not api_data:
        print("Could not retrieve current data. Exiting.")
        return None

    # ค้นหาสถานี "อินทร์บุรี" จากรายการ data ใน api_data
    target_station = None
    for station in api_data.get('data', []):
        name_th = station.get('station', {}).get('station_name', {}).get('th', '')
        if STATION_NAME_TO_FIND in name_th:
            target_station = station
            break

    if not target_station:
        print(f"Could not find station '{STATION_NAME_TO_FIND}' in the API response.")
        return None

    # แปลงข้อมูลที่ต้องการ
    water_level = target_station.get('wl_tele', {}).get('storage_level')
    bank_level = target_station.get('station', {}).get('ground_level')
    overflow = None
    if water_level is not None and bank_level is not None:
        overflow = water_level - bank_level

    result = {
        "station": STATION_NAME_TO_FIND,
        "water_level": water_level,
        "bank_level": bank_level,
        "overflow": overflow,
        "timestamp": datetime.now(TIMEZONE_THAILAND).isoformat()
    }
    print(f"Result: {result}")
    return result


def read_last_data(filepath):
    if os.path.isfile(filepath):
        with open(filepath, 'r') as f:
            return f.read().strip()
    return None

def write_data(filepath, data_str):
    with open(filepath, 'w') as f:
        f.write(data_str)

def send_line_message(data):
    from linebot import LineBotApi
    from linebot.models import TextSendMessage
    line_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    msg = (f"สถานี {data['station']} ระดับน้ำ: {data['water_level']} m "
           f"(bank level: {data['bank_level']} m, overflow: {data['overflow']} m)\n"
           f"เวลา: {data['timestamp']}")
    line_api.push_message(LINE_TARGET_ID, TextSendMessage(text=msg))


def main():
    data = get_inburi_river_data_from_api()
    if not data:
        return
    current = f"{data['water_level']:.2f}"
    last = read_last_data(LAST_DATA_FILE)
    print(f"Current data string: {current}")
    print(f"Last data string: {last}")
    if current != last:
        print("Data has changed! Sending notification...")
        send_line_message(data)
        write_data(LAST_DATA_FILE, current)
    else:
        print("Data has not changed. No action needed.")

if __name__ == "__main__":
    main()
