import os
import json
import requests
from datetime import datetime, timedelta

# --- Constants and configuration ---
DATA_FILE = "inburi_bridge_data.json"
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/broadcast"
NOTIFICATION_THRESHOLD = 0.01 # แจ้งเตือนเมื่อระดับน้ำเปลี่ยนเกิน 1 ซม.

# Correct and final API URL
API_URL = "https://api-v3.thaiwater.net/api/v1/public/tele_station_data?station_type=waterlevel&station_id=C.2"

def load_last_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def fetch_and_parse_data():
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        api_data = response.json().get("data", [])
        if not api_data:
            return None

        station_data = api_data[0]
        water_level = float(station_data.get("water_level", 0.0))
        bank_level = float(station_data.get("ground_level", 0.0))
        timestamp_str = station_data.get("time")
        status = station_data.get("status", {}).get("th", "N/A")

        dt_object_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        bkk_time = dt_object_utc + timedelta(hours=7)
        formatted_time = bkk_time.strftime('%Y-%m-%d %H:%M:%S')

        return {
            "station_name": station_data.get("station_name", {}).get("th", "สถานีอินทร์บุรี"),
            "water_level": water_level, "bank_level": bank_level,
            "below_bank": bank_level - water_level, "status": status,
            "time": formatted_time
        }
    except Exception as e:
        print(f"--> ERROR fetching or parsing data: {e}")
        return None

def send_line_message(text):
    if not LINE_ACCESS_TOKEN:
        return
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messages": [{"type": "text", "text": text}]}
    try:
        requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
        print("--> LINE Sent Successfully.")
    except Exception as e:
        print(f"--> LINE Send ERROR: {e}")

def main():
    print("--- Running Final Script ---")
    last_data = load_last_data()
    data = fetch_and_parse_data()

    if not data:
        print("--- EXIT: Could not fetch new data. ---")
        return
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    if not last_data:
        print("--> First run. Data saved. No notification.")
        return

    diff = data["water_level"] - last_data.get("water_level", 0.0)
    
    if abs(diff) < NOTIFICATION_THRESHOLD:
        print(f"--> No significant change ({diff:.3f}m). No notification.")
        return

    trend_text = f"น้ำ{'ขึ้น' if diff > 0 else 'ลง'}"
    status_emoji = '🔴' if 'ล้นตลิ่ง' in data['status'] else '⚠️' if 'เฝ้าระวัง' in data['status'] else '✅'
    distance_text = f"{'ต่ำกว่า' if data['below_bank'] >= 0 else 'สูงกว่า'}ตลิ่ง {abs(data['below_bank']):.2f} ม."
    
    message = ( f"💧 รายงานระดับน้ำ {data['station_name']}\n\n"
                f"🌊 ระดับปัจจุบัน: {data['water_level']:.2f} ม.รทก. ({trend_text})\n\n"
                f"📊 สถานะ: {status_emoji} {data['status']} ({distance_text})\n\n"
                f"⏰ เวลา: {data['time']}")
    
    print("--- Change detected! Sending LINE message. ---")
    send_line_message(message)
    print("--- Script Finished ---")

if __name__ == "__main__":
    main()
