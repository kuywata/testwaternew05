import os
import json
import requests
from datetime import datetime, timedelta

# --- ค่าคงที่ ---
DATA_FILE = "inburi_bridge_data.json"
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/broadcast"
NOTIFICATION_THRESHOLD = 0.01  # แจ้งเตือนเมื่อระดับน้ำเปลี่ยนเกิน 1 ซม.

# !!! URL ที่ถูกต้องและทดสอบแล้ว !!!
API_URL = "https://api-v3.thaiwater.net/api/v1/tele/station/C.2"

def load_last_data():
    """โหลดข้อมูลที่บันทึกไว้ล่าสุดจากไฟล์ JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def fetch_data():
    """ดึงข้อมูลล่าสุดจาก API ของ ThaiWater"""
    try:
        response = requests.get(API_URL, timeout=20)
        response.raise_for_status()  # ทำให้เกิด Error ถ้าสถานะไม่ใช่ 200 OK
        
        api_data = response.json().get("data", [{}])[0].get("tele_station_waterlevel", {})
        if not api_data:
            print("--> ERROR: ไม่พบข้อมูล waterlevel ใน API response")
            return None

        water_level = float(api_data.get("storage_waterlevel", 0.0))
        bank_level = float(api_data.get("ground_waterlevel", 0.0))
        timestamp_str = api_data.get("storage_datetime")
        status = api_data.get("waterlevel_status", {}).get("waterlevel_status_name", "N/A")

        dt_object_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        bkk_time = dt_object_utc + timedelta(hours=7)
        
        return {
            "station_name": "สถานีอินทร์บุรี (C.2)",
            "water_level": water_level,
            "bank_level": bank_level,
            "below_bank": bank_level - water_level,
            "status": status,
            "time": bkk_time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"--> ERROR fetching data: {e}")
        return None

def send_line_message(text):
    """ส่งข้อความแจ้งเตือนไปที่ LINE"""
    if not LINE_ACCESS_TOKEN:
        print("--> SKIPPING LINE: No Access Token.")
        return
        
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messages": [{"type": "text", "text": text}]}
    try:
        requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
        print("--> LINE message sent successfully.")
    except Exception as e:
        print(f"--> ERROR sending LINE message: {e}")

def main():
    """ฟังก์ชันหลักในการทำงาน"""
    print("--- Running Water Level Checker (API Final Version) ---")
    last_data = load_last_data()
    print(f"Old Level: {last_data.get('water_level', 'None')}")
    
    current_data = fetch_data()
    if not current_data:
        print("--- EXIT: Failed to fetch new data. ---")
        return
    print(f"New Level: {current_data['water_level']}")

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

    if not last_data:
        print("--> First run, data saved. No notification will be sent.")
        return

    diff = current_data["water_level"] - last_data.get("water_level", 0.0)
    
    if abs(diff) < NOTIFICATION_THRESHOLD:
        print(f"--> Change ({diff:.3f}m) is below threshold. No notification needed.")
        return

    trend_text = "น้ำขึ้น" if diff > 0 else "น้ำลง"
    status_emoji = '🔴' if 'ล้นตลิ่ง' in current_data['status'] else '⚠️' if 'เฝ้าระวัง' in current_data['status'] else '✅'
    
    message = (f"💧 แจ้งเตือนระดับน้ำ {current_data['station_name']}\n\n"
               f"🌊 ระดับปัจจุบัน: {current_data['water_level']:.2f} ม.รทก.\n"
               f"   (เปลี่ยนแปลง {diff:+.2f} ม. - {trend_text})\n\n"
               f"📊 สถานะ: {status_emoji} {current_data['status']}\n\n"
               f"⏰ เวลา: {current_data['time']}")
    
    print("--- Significant change detected! Sending LINE message. ---")
    send_line_message(message)
    print("--- Script finished successfully. ---")

if __name__ == "__main__":
    main()
