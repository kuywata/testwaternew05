import requests
import json
import os
from datetime import datetime
import pytz

# --- ⚙️ การตั้งค่าหลัก ---
STATION_CODE = "C.13" # รหัสสถานีสะพานอินทร์บุรี
API_URL = "https://webservice.hii.or.th/api/v2/waterlevel/station/realtime"
STATION_NAME = "สะพานอินทร์บุรี"
DATA_FILE = "inburi_bridge_data.json"
TIMEZONE = pytz.timezone("Asia/Bangkok")

# --- 🤫 ดึงค่า Secrets สำหรับ LINE ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')


def get_water_level_data():
    """ดึงข้อมูลระดับน้ำล่าสุดจาก API ของ HII"""
    try:
        print(f"กำลังดึงข้อมูลสถานี {STATION_CODE} ({STATION_NAME})...")
        response = requests.get(f"{API_URL}?station_code={STATION_CODE}", timeout=20)
        response.raise_for_status()
        api_response_data = response.json()

        if not api_response_data.get("data"):
            print("API ตอบกลับมาแต่ไม่มีข้อมูล")
            return None

        station_data = api_response_data["data"][0]
        tele_data = station_data.get("tele_waterlevel", {})

        water_level_value = tele_data.get("water_level", {}).get("value")
        ground_level_value = tele_data.get("ground_level", {}).get("value")

        if water_level_value is None or ground_level_value is None:
             print("ข้อมูลระดับน้ำหรือระดับตลิ่งที่ได้รับจาก API เป็นค่าว่าง")
             return None

        return {
            "station_code": station_data["station_code"],
            "water_level": water_level_value,
            "ground_level": ground_level_value,
            "time": station_data["tele_waterlevel_datetime"],
        }

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        return None


def send_line_message(message):
    """ส่งข้อความแจ้งเตือนไปที่ LINE"""
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
