import requests
import json
import os
from datetime import datetime
import pytz

# --- ⚙️ การตั้งค่าหลัก ---
STATION_CODE = "C.13" # รหัสสถานีสะพานอินทร์บุรี
API_URL = "https://webservice.hii.or.th/api/v2/waterlevel/station/realtime" # API ใหม่ที่เสถียรกว่า
STATION_NAME = "สะพานอินทร์บุรี"
DATA_FILE = "inburi_bridge_data.json"
TIMEZONE = pytz.timezone("Asia/Bangkok")

# --- 🤫 ดึงค่า Secrets สำหรับ LINE ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')


def get_water_level_data():
    """ดึงข้อมูลระดับน้ำล่าสุดจาก API ของ HII"""
    try:
        print(f"กำลังดึงข้อมูลสถานี {STATION_CODE} ({STATION_NAME}) จาก API...")
        response = requests.get(f"{API_URL}?station_code={STATION_CODE}", timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # ตรวจสอบว่ามีข้อมูลใน list หรือไม่
        if not data.get("data"):
            print("API ตอบกลับมาแต่ไม่มีข้อมูล")
            return None

        station_data = data["data"][0]
        tele_data = station_data.get("tele_waterlevel", {})
        
        # จัดรูปแบบข้อมูลให้พร้อมใช้งาน
        return {
            "station_code": station_data["station_code"],
            "water_level": tele_data.get("water_level", {}).get("value"),
            "ground_level": tele_data.get("ground_level", {}).get("value"),
            "time": station_data["tele_waterlevel_datetime"],
        }

    except requests.exceptions.RequestException as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ API: {e}")
        return None
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"เกิดข้อผิดพลาดในการอ่านข้อมูล JSON: {e}")
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
    print("===== เริ่มการทำงานของระบบแจ้งเตือนระดับน้ำ =====")
    
    # 1. อ่านข้อมูลเก่าที่บันทึกไว้
    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            last_data = json.load(f)

    # 2. ดึงข้อมูลใหม่
    current_data = get_water_level_data()

    if current_data and current_data.get("water_level") is not None:
        # 3. เปรียบเทียบข้อมูลเก่า-ใหม่
        if not last_data or last_data.get("time") != current_data.get("time"):
            print("พบข้อมูลอัปเดตใหม่!")

            # 4. คำนวณแนวโน้ม
            trend_symbol = "―" # ทรงตัว
            if last_data.get("water_level"):
                if current_data["water_level"] > last_data["water_level"]:
                    trend_symbol = "▲ ขึ้น"
                elif current_data["water_level"] < last_data["water_level"]:
                    trend_symbol = "▼ ลง"

            # 5. สร้างข้อความแจ้งเตือน
            dt_object = datetime.fromisoformat(current_data["time"]).astimezone(TIMEZONE)
            time_str = dt_object.strftime("%H:%M น. วันที่ %d/%m/%Y")
            
            message = (
                f"🌊 แจ้งเตือนระดับน้ำ {STATION_NAME}\n"
                f"({time_str})\n"
                f"━━━━━━━━━━━━━━\n"
                f"ระดับน้ำล่าสุด: **{current_data['water_level']:.2f} ม.**\n"
                f"แนวโน้ม: **{trend_symbol}**\n\n"
                f"ระดับตลิ่ง: {current_data['ground_level']:.2f} ม."
            )
            
            print("กำลังส่งการแจ้งเตือน...")
            send_line_message(message)

            # 6. บันทึกข้อมูลใหม่
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=4)
            print(f"บันทึกข้อมูลล่าสุดลงไฟล์ {DATA_FILE} สำเร็จ")

        else:
            print("ข้อมูลไม่มีการเปลี่ยนแปลง")
    else:
        print("ไม่สามารถดึงข้อมูลใหม่ได้ในรอบนี้")

    print("===== ระบบทำงานเสร็จสิ้น =====")
