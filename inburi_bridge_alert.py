import os
import json
import requests
from datetime import datetime, timedelta

# --- Constants and configuration ---
DATA_FILE = "inburi_bridge_data.json"
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/broadcast"
# Notify if water level changes by this much (in meters). 0.01 = 1 cm.
NOTIFICATION_THRESHOLD = 0.01

# Correct API URL
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
            print("--> API response is empty.")
            return None

        station_data = api_data[0]

        water_level = station_data.get("water_level")
        bank_level = station_data.get("ground_level")
        timestamp_str = station_data.get("time")
        status = station_data.get("status")

        water_level = float(water_level) if water_level is not None else 0.0
        bank_level = float(bank_level) if bank_level is not None else 0.0

        dt_object_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        bkk_time = dt_object_utc + timedelta(hours=7)
        formatted_time = bkk_time.strftime('%Y-%m-%d %H:%M:%S')

        return {
            "station_name": station_data.get("station_name", {}).get("th", "สถานีอินทร์บุรี"),
            "water_level": water_level,
            "bank_level": bank_level,
            "below_bank": bank_level - water_level,
            "status": status.get("th", "ไม่พบสถานะ"),
            "time": formatted_time
        }
    except Exception as e:
        print(f"--> ERROR: {e}")
        return None

def send_line_message(text):
    if not LINE_ACCESS_TOKEN:
        print("--> SKIPPING LINE: No token.")
        return
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    payload = {"messages": [{"type": "text", "text": text}]}
    try:
        resp = requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            print("--> LINE Sent Successfully.")
        else:
            print(f"--> LINE Send Failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"--> LINE Send ERROR: {e}")

def main():
    print("--- Running Script (Final Logic) ---")
    last_data = load_last_data()
    print(f"Old Data Level: {last_data.get('water_level', 'None')}")

    data = fetch_and_parse_data()
    if not data:
        print("--- EXIT: Could not fetch new data. ---")
        return
    print(f"New Data Level: {data['water_level']}")

    # --- NEW NOTIFICATION LOGIC ---
    # Always save the latest data, regardless of notification
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"--> New data saved to {DATA_FILE}")

    if not last_data:
        print("--> First run, saving data but not notifying.")
        return

    diff = data["water_level"] - last_data.get("water_level", 0.0)

    # Notify only if the water level has changed significantly
    if abs(diff) < NOTIFICATION_THRESHOLD:
        print(f"--> Water level change ({diff:.3f}m) is less than threshold ({NOTIFICATION_THRESHOLD}m). No notification needed.")
        return
    # --- END OF NEW LOGIC ---

    trend_text = f"น้ำ{'ขึ้น' if diff > 0 else 'ลง'}"
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

    print("--- Change detected! Preparing LINE message ---")
    print(message)
    send_line_message(message)

    print("--- Script Finished ---")

if __name__ == "__main__":
    main()
