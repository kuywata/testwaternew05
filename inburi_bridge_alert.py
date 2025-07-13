import requests
import json
import os
import time
from datetime import datetime
import pytz

# --- ⚙️ การตั้งค่าหลัก ---
STATION_CODE = "C.13" 
API_URL = "https://webservice.hii.or.th/api/v2/waterlevel/station/realtime"
STATION_NAME = "สะพานอินทร์บุรี"
DATA_FILE = "inburi_bridge_data.json" # แก้ไขชื่อไฟล์ให้ตรงกับใน .yml
TIMEZONE = pytz.timezone("Asia/Bangkok")
RETRY_COUNT = 3 # กำหนดให้ลองใหม่ 3 ครั้ง
RETRY_DELAY = 10 # หน่วงเวลา 10 วินาทีก่อนลองใหม่

# ... (ส่วน send_line_message เหมือนเดิม) ...
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')

def get_water_level_data():
    """ดึงข้อมูลระดับน้ำล่าสุดจาก API ของ HII พร้อมระบบ Retry"""
    for i in range(RETRY_COUNT):
        try:
            print(f"กำลังดึงข้อมูลสถานี {STATION_CODE} (ครั้งที่ {i + 1}/{RETRY_COUNT})...")
            response = requests.get(f"{API_URL}?station_code={STATION_CODE}", timeout=20)
            response.raise_for_status()
            api_response_data = response.json()

            if not api_response_data.get("data"):
                print("API ตอบกลับมาแต่ไม่มีข้อมูล")
                return None

            # ... (ส่วนประมวลผลข้อมูลเหมือนเดิม) ...

            print("ดึงข้อมูลสำเร็จ!")
            return {
                # ... data ...
            }

        except requests.exceptions.RequestException as e:
            print(f"ครั้งที่ {i + 1} ล้มเหลว: {e}")
            if i < RETRY_COUNT - 1:
                print(f"จะลองใหมในอีก {RETRY_DELAY} วินาที...")
                time.sleep(RETRY_DELAY)
            else:
                print("ลองครบ 3 ครั้งแล้วยังล้มเหลว")
                return None
    return None

# ... (โค้ดส่วนที่เหลือทั้งหมดเหมือนเดิม) ...

def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("ไม่ได้ตั้งค่า LINE credentials, ข้ามการส่ง")
        return

    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    payload = {'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}]}

    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("ส่งข้อความ LINE สำเร็จ!")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการส่ง LINE: {e}")

if __name__ == "__main__":
    print("===== เริ่มการทำงาน =====")

    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try: last_data = json.load(f)
            except: pass

    current_data = get_water_level_data()

    if current_data:
        if not last_data or last_data.get("time") != current_data.get("time"):
            print("พบข้อมูลอัปเดตใหม่!")

            trend_symbol = "― ทรงตัว"
            if last_data.get("water_level") is not None:
                if current_data["water_level"] > last_data["water_level"]:
                    trend_symbol = "▲ ขึ้น"
                elif current_data["water_level"] < last_data["water_level"]:
                    trend_symbol = "▼ ลง"

            dt_object = datetime.fromisoformat(current_data["time"]).astimezone(TIMEZONE)
            time_str = dt_object.strftime("%H:%M น. (%d/%m/%y)")

            message = (
                f"🌊 แจ้งเตือนระดับน้ำ {STATION_NAME}\n"
                f"({time_str})\n"
                f"━━━━━━━━━━━━━━\n"
                f"ระดับน้ำ: **{current_data['water_level']:.2f} ม.**\n"
                f"แนวโน้ม: **{trend_symbol}**\n\n"
                f"ระดับตลิ่งอยู่ที่ {current_data['ground_level']:.2f} ม."
            )

            send_line_message(message)

            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=4)
            print(f"บันทึกข้อมูลล่าสุดลงไฟล์ {DATA_FILE} สำเร็จ")

        else:
            print("ข้อมูลไม่มีการเปลี่ยนแปลง")
    else:
        print("ไม่สามารถดึงข้อมูลใหม่ได้ในรอบนี้")

    print("===== จบการทำงาน =====")
