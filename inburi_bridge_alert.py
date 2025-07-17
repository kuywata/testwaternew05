import os
import json
import time
import requests
from bs4 import BeautifulSoup

# --- Configurations ---
DATA_FILE = "inburi_bridge_data.json"

# อ่าน threshold จาก env; หากไม่มีหรือแปลงไม่สำเร็จ ใช้ default = 0.10 เมตร
_raw = os.getenv("NOTIFICATION_THRESHOLD_M")
try:
    NOTIFICATION_THRESHOLD = float(_raw) if _raw else 0.10
except ValueError:
    print(f"--> ❗ WARN: ไม่สามารถแปลง NOTIFICATION_THRESHOLD_M='{_raw}' เป็น float, ใช้ default=0.10")
    NOTIFICATION_THRESHOLD = 0.10

LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_TARGET_ID = os.getenv("LINE_TARGET_ID")

def send_line_message(message: str):
    if not LINE_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("--> ❌ LINE token/target ไม่ถูกตั้งค่า!")
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_TARGET_ID,
        "messages": [{"type": "text", "text": message}]
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.status_code != 200:
        print(f"--> ❌ ส่ง LINE ไม่สำเร็จ: {resp.status_code} {resp.text}")

def get_water_data():
    url = "https://singburi.thaiwater.net/wl"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.find("table", {"class": "table-striped"})
    if not table:
        print("--> ไม่เจอตารางข้อมูล")
        return None

    for row in table.find_all("tr"):
        th = row.find("th")
        cols = row.find_all("td")
        if th and "อินทร์บุรี" in th.text and len(cols) >= 3:
            water_level = float(cols[1].text.strip())
            bank_level = float(cols[2].text.strip())
            status = cols[3].text.strip() if len(cols) > 3 else "-"
            below_bank = round(bank_level - water_level, 2)
            current_time = time.strftime("%H:%M น.", time.localtime())
            return {
                "station_name": "อินทร์บุรี",
                "water_level": water_level,
                "bank_level": bank_level,
                "status": status,
                "below_bank": below_bank,
                "time": current_time,
            }
    return None

def main():
    try:
        print("--- เริ่มทำงาน inburi_bridge_alert.py ---")

        # โหลดข้อมูลเก่าสุด
        last_data = {}
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                last_data = json.load(f)
            print(f"โหลดข้อมูลเก่า: {last_data}")

        # ดึงข้อมูลใหม่
        data = get_water_data()
        if not data:
            print("--> ไม่มีข้อมูลใหม่, จบการทำงาน")
            return

        # ถ้าค่าน้ำเปลี่ยนจากครั้งก่อน
        if last_data.get("water_level") != data["water_level"]:
            msg = (
                f"🌊 สถานี {data['station_name']}:\n"
                f"• ระดับน้ำ: {data['water_level']} ม.\n"
                f"• ระดับตลิ่ง: {data['bank_level']} ม.\n"
                f"• สถานะ: {data['status']}\n"
                f"• ห่างจากตลิ่ง: {data['below_bank']} ม.\n"
                f"🕒 เวลา: {data['time']}"
            )
            print(msg)
            send_line_message(msg)
            # บันทึกข้อมูลครั้งล่าสุด
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            print("--> ระดับน้ำไม่เปลี่ยน ปิดการแจ้งเตือน")

        print("--- จบ script ---")
    except Exception as e:
        import traceback
        print("❌ เกิดข้อผิดพลาด:", e)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()