import requests
import json
import os
import time
from datetime import datetime
import pytz

# --- ⚙️ การตั้งค่าหลัก ---
STATION_CODE = "C.13" # รหัสสถานีของ HII สำหรับสะพานอินทร์บุรี
API_URL = "https://webservice.hii.or.th/api/v2/waterlevel/station/realtime"
STATION_NAME = "สะพานอินทร์บุรี"
DATA_FILE = "inburi_bridge_data.json" # ชื่อไฟล์สำหรับบันทึกข้อมูลล่าสุด
TIMEZONE = pytz.timezone("Asia/Bangkok")
RETRY_COUNT = 3      # กำหนดให้ลองดึงข้อมูลใหม่ 3 ครั้งหากล้มเหลว
RETRY_DELAY = 10     # หน่วงเวลา 10 วินาทีก่อนลองใหม่

# --- 🔑 การตั้งค่า LINE (ดึงจาก GitHub Secrets) ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID') # ID ของผู้ใช้, กลุ่ม, หรือห้องที่จะรับการแจ้งเตือน

def get_water_level_data():
    """ดึงข้อมูลระดับน้ำล่าสุดจาก API ของ HII พร้อมระบบ Retry"""
    for i in range(RETRY_COUNT):
        try:
            print(f"กำลังดึงข้อมูลสถานี {STATION_CODE} (ครั้งที่ {i + 1}/{RETRY_COUNT})...")
            response = requests.get(f"{API_URL}?station_code={STATION_CODE}", timeout=20)
            response.raise_for_status() # หาก status code ไม่ใช่ 2xx จะเกิด Exception
            api_data = response.json()

            # ตรวจสอบว่ามีข้อมูลใน response หรือไม่
            if not api_data.get("data"):
                print("API ตอบกลับมาแต่ไม่มีข้อมูล (data is empty)")
                return None

            # ดึงข้อมูลส่วนที่ต้องการจากโครงสร้าง JSON ของ HII
            latest_data = api_data["data"][0]
            water_level_data = latest_data.get("water_level", {})
            station_data = latest_data.get("station", {})

            # ดึงค่าที่ต้องการออกมา
            time_str = latest_data.get("data_time")
            water_level = water_level_data.get("value")
            ground_level = station_data.get("ground_level") # ระดับตลิ่ง

            # ตรวจสอบว่าได้ข้อมูลครบถ้วนหรือไม่
            if all([time_str, water_level is not None, ground_level is not None]):
                print("ดึงข้อมูลสำเร็จ!")
                return {
                    "time": time_str,
                    "water_level": float(water_level),
                    "ground_level": float(ground_level)
                }
            else:
                print("ข้อมูลที่ได้รับจาก API ไม่สมบูรณ์")
                return None

        except requests.exceptions.RequestException as e:
            print(f"ครั้งที่ {i + 1} ล้มเหลว: {e}")
            if i < RETRY_COUNT - 1:
                print(f"จะลองใหมในอีก {RETRY_DELAY} วินาที...")
                time.sleep(RETRY_DELAY)
            else:
                print("ลองครบ 3 ครั้งแล้วยังล้มเหลว")
                return None
    return None

def send_line_message(message):
    """ส่งข้อความแจ้งเตือนผ่าน LINE Messaging API"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("⚠️ ไม่ได้ตั้งค่า LINE_CHANNEL_ACCESS_TOKEN หรือ LINE_TARGET_ID, ข้ามการส่งข้อความ")
        return

    print("กำลังส่งข้อความไปที่ LINE...")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {
        'to': LINE_TARGET_ID,
        'messages': [{'type': 'text', 'text': message}]
    }

    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ ส่งข้อความ LINE สำเร็จ!")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการส่ง LINE: {e}")

if __name__ == "__main__":
    print(f"===== เริ่มการทำงาน: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} =====")

    # โหลดข้อมูลล่าสุดที่เคยบันทึกไว้
    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                last_data = json.load(f)
                print(f"โหลดข้อมูลเก่าสำเร็จ: ระดับน้ำ {last_data.get('water_level')} ม. ({last_data.get('time')})")
            except json.JSONDecodeError:
                print("ไฟล์ข้อมูลเก่ามีปัญหา, จะทำการสร้างใหม่")

    # ดึงข้อมูลใหม่
    current_data = get_water_level_data()

    if current_data:
        # เปรียบเทียบเวลาของข้อมูลใหม่กับข้อมูลเก่า
        if not last_data or last_data.get("time") != current_data.get("time"):
            print("พบข้อมูลอัปเดตใหม่! กำลังเตรียมส่งการแจ้งเตือน...")

            # คำนวณแนวโน้ม
            trend_symbol = "―"
            trend_text = "ทรงตัว"
            if last_data.get("water_level") is not None:
                if current_data["water_level"] > last_data["water_level"]:
                    trend_symbol = "▲"
                    trend_text = "เพิ่มขึ้น"
                elif current_data["water_level"] < last_data["water_level"]:
                    trend_symbol = "▼"
                    trend_text = "ลดลง"

            # คำนวณระยะห่างจากตลิ่ง
            below_bank = current_data['ground_level'] - current_data['water_level']
            status = f"ต่ำกว่าตลิ่ง {below_bank:.2f} ม."
            if below_bank < 0:
                status = f"สูงกว่าตลิ่ง {abs(below_bank):.2f} ม."

            # แปลงเวลาให้สวยงาม
            dt_object = datetime.fromisoformat(current_data["time"]).astimezone(TIMEZONE)
            time_str = dt_object.strftime("%d/%m/%Y %H:%M น.")

            # สร้างข้อความที่จะส่ง
            message = (
                f"🌊 **ระดับน้ำ {STATION_NAME}**\n"
                f"🗓️ {time_str}\n"
                f"━━━━━━━━━━━━━━\n"
                f"💧 ระดับน้ำ: **{current_data['water_level']:.2f}** ม.รทก.\n"
                f"📊 แนวโน้ม: **{trend_symbol} {trend_text}**\n"
                f"〰️ ({status})"
            )

            send_line_message(message)

            # บันทึกข้อมูลใหม่ลงไฟล์
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=4)
            print(f"บันทึกข้อมูลล่าสุดลงไฟล์ {DATA_FILE} สำเร็จ")

        else:
            print("ข้อมูลไม่มีการเปลี่ยนแปลง, ข้ามการแจ้งเตือน")
    else:
        print("ไม่สามารถดึงข้อมูลใหม่ได้ในรอบนี้")

    print("===== จบการทำงาน =====")
