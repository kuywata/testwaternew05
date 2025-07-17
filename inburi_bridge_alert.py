import os
import json
import requests

# --- Constants and configuration ---
DATA_FILE = "inburi_bridge_data.json"
NOTIFICATION_THRESHOLD = float(os.getenv("NOTIFICATION_THRESHOLD_M", "0.10"))
NEAR_BANK_THRESHOLD    = float(os.getenv("NEAR_BANK_THRESHOLD_M", "1.0"))
LINE_ACCESS_TOKEN      = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL           = "https://api.line.me/v2/bot/message/broadcast"

# API Endpoint for Inburi Station (C.2)
API_URL = "https://api-v3.thaiwater.net/api/v1/stations/tele_station/C.2?include=basin,sub_basin,province,amphoe,tambol,rid_center,agency"

def load_last_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {} # Return empty dict if no file

def fetch_and_parse_data():
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        api_data = response.json()
        station_data = api_data.get("data", {})
        water_level = station_data.get("tele_station_waterlevel", {}).get("storage_waterlevel")
        bank_level = station_data.get("tele_station_waterlevel", {}).get("ground_waterlevel")
        timestamp = station_data.get("tele_station_waterlevel", {}).get("storage_datetime")
        status = station_data.get("tele_station_waterlevel", {}).get("waterlevel_status", {}).get("waterlevel_status_name")
        water_level = float(water_level) if water_level is not None else 0.0
        bank_level = float(bank_level) if bank_level is not None else 0.0
        return {
            "station_name": station_data.get("tele_station_name", {}).get("th", "ไม่พบชื่อสถานี"),
            "water_level": water_level,
            "bank_level": bank_level,
            "below_bank": bank_level - water_level,
            "status": status if status else "ไม่พบสถานะ",
            "time": timestamp.replace("T", " ").split("+")[0] if timestamp else "ไม่มีข้อมูลเวลา"
        }
    except Exception as e:
        print(f"--> ❌ เกิดข้อผิดพลาด: {e}")
        return None

def send_line_message(text):
    if not LINE_ACCESS_TOKEN:
        print("--> ⚠️ ข้ามการส่ง LINE เพราะไม่มี TOKEN")
        return
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    payload = {"messages": [{"type": "text", "text": text}]}
    try:
        resp = requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            print("--> ✅ ส่ง LINE สำเร็จ")
        else:
            print(f"--> ❌ ส่ง LINE ล้มเหลว: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"--> ❌ เกิดข้อผิดพลาดในการส่ง LINE: {e}")

def main():
    print("--- เริ่มทำงาน (API Version) ---")
    last_data = load_last_data()
    print(f"ข้อมูลเก่า: {last_data.get('water_level', 'ไม่มี')}")
    data = fetch_and_parse_data()
    if not data:
        print("--- จบการทำงานเพราะดึงข้อมูลใหม่ไม่ได้ ---")
        return
    print(f"ข้อมูลใหม่: {data['water_level']}")
    if not last_data or data["time"] == last_data.get("time"):
        print("--> ข้อมูลไม่เปลี่ยนแปลง ข้ามการแจ้งเตือน")
        print("--- จบการทำงาน ---")
        return
    diff = data["water_level"] - last_data.get("water_level", 0.0)
    trend_text = f"น้ำ{'ขึ้น' if diff > 0 else 'ลง'}" if diff != 0 else "คงที่"
    diff_symbol = '+' if diff >= 0 else ''
    status_emoji = '🔴' if 'ล้นตลิ่ง' in data['status'] else '⚠️' if 'เฝ้าระวัง' in data['status'] else '✅'
    distance_text = f"{'ต่ำกว่า' if data['below_bank'] >= 0 else 'สูงกว่า'}ตลิ่ง {abs(data['below_bank']):.2f} ม."
    message = (
        f"💧 รายงานระดับน้ำ {data['station_name']}\n\n"
        f"🌊 ระดับปัจจุบัน: {data['water_level']:.2f} ม.รทก.\n"
        f"({trend_text} {diff_symbol}{abs(diff):.2f} ม.)\n\n"
        f"📊 สถานะ: {status_emoji} {data['status']}\n"
        f"({distance_text})\n\n"
        f"⏰ เวลา: {data['time']}"
    )
    print("--- สร้างข้อความสำหรับส่ง LINE ---")
    print(message)
    send_line_message(message)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"--> ✅ บันทึกข้อมูลใหม่ลงไฟล์ {DATA_FILE}")
    print("--- จบการทำงาน ---")

if __name__ == "__main__":
    main()
