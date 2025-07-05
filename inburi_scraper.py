import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
import pytz

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

# --- การตั้งค่าสำหรับสคริปต์นี้โดยเฉพาะ ---
STATION_URL = "https://water.rid.go.th/tele/waterlevel/w-chaophaya"
STATION_NAME = "C.35"  # รหัสสถานี อ.อินทร์บุรี
LAST_DATA_FILE = 'last_inburi_data.txt' # ไฟล์เก็บข้อมูลล่าสุดของอินทร์บุรี

def get_inburi_river_data():
    """ดึงข้อมูลระดับน้ำ, ระดับตลิ่ง และคำนวณส่วนต่างจากสถานี C.35 อินทร์บุรี"""
    try:
        print(f"Fetching data from RID website for station {STATION_NAME}...")
        # เพิ่ม verify=False เพื่อข้ามการตรวจสอบ SSL Certificate
        response = requests.get(STATION_URL, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # ค้นหาตารางข้อมูลทั้งหมด
        tables = soup.find_all('table', class_='table-striped')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                # เช็คว่าแถวนี้คือสถานี C.35 หรือไม่
                if cells and STATION_NAME in cells[0].text:
                    station_name_full = cells[0].text.strip()
                    water_level_str = cells[1].text.strip()
                    bank_level_str = cells[3].text.strip() # ระดับตลิ่งคือคอลัมน์ที่ 4

                    print(f"Found station: {station_name_full}")
                    print(f"  - Water Level: {water_level_str}")
                    print(f"  - Bank Level: {bank_level_str}")

                    # แปลงเป็นตัวเลข
                    water_level = float(water_level_str)
                    bank_level = float(bank_level_str)

                    # คำนวณส่วนต่างจากตลิ่ง
                    overflow = water_level - bank_level

                    # สร้าง Dictionary เพื่อส่งข้อมูลกลับ
                    return {
                        "station": station_name_full,
                        "water_level": water_level,
                        "bank_level": bank_level,
                        "overflow": overflow
                    }

        print(f"Could not find station {STATION_NAME} in the tables.")
        return None

    except (requests.exceptions.RequestException, ValueError, IndexError) as e:
        print(f"An error occurred in get_inburi_river_data: {e}")
        return None

def send_line_message(data):
    """ส่งข้อความแจ้งเตือนระดับน้ำของอินทร์บุรี"""
    now_thailand = datetime.now(TIMEZONE_THAILAND)
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M น.")

    # กำหนดสถานะและไอคอน
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

    # สร้างสตริงข้อมูลปัจจุบันเพื่อเปรียบเทียบและบันทึก
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
