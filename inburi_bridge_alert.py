import os
import json
import time
import requests
import shutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# --- Constants and configuration ---
DATA_FILE = "inburi_bridge_data.json"
# NOTIFICATION_THRESHOLD in meters (e.g., 0.10 for 10 cm)
NOTIFICATION_THRESHOLD = float(os.getenv("NOTIFICATION_THRESHOLD_M", "0.10"))
# NEAR_BANK_THRESHOLD in meters (e.g., 1.0 for 1 m)
NEAR_BANK_THRESHOLD    = float(os.getenv("NEAR_BANK_THRESHOLD_M", "1.0"))
# LINE Messaging API token
LINE_ACCESS_TOKEN      = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL           = "https://api.line.me/v2/bot/message/broadcast"


def load_last_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # Default initial state
    return {
        "station_name": "อินทร์บุรี",
        "water_level": 0.0,
        "bank_level": 0.0,
        "below_bank": 0.0,
        "status": "",
        "time": ""
    }


def fetch_page(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium-browser")
    driver = webdriver.Chrome(service=Service(), options=options)
    driver.get(url)
    time.sleep(7)
    html = driver.page_source
    driver.quit()
    return html


def parse_data(html):
    soup = BeautifulSoup(html, "html.parser")
    # --- โค้ด parsing ข้อมูลเหมือนเดิม (adapt as in original) ---
    station_name = soup.select_one(".station-title").text.strip()
    water_level   = float(soup.select_one("#waterLevel").text)
    bank_level    = float(soup.select_one("#bankLevel").text)
    below_bank    = bank_level - water_level
    status        = "น้ำปกติ" if water_level < bank_level else "วิกฤต"
    timestamp     = soup.select_one(".updated-time").text.strip()
    return {
        "station_name": station_name,
        "water_level": water_level,
        "bank_level": bank_level,
        "below_bank": below_bank,
        "status": status,
        "time": timestamp
    }


def send_line_message(text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {"messages": [{"type": "text", "text": text} ]}
    resp = requests.post(LINE_API_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        print(f"--> ❌ ส่ง LINE ล้มเหลว: {resp.status_code} {resp.text}")
    else:
        print("--> ✅ ส่ง LINE สำเร็จ")


def main():
    print(f"--- เริ่มทำงาน {__file__} ---")
    url = "https://waterdata.dwr.go.th/river-level/"  # ปรับ URL ให้ตรงกับต้นทาง
    last_data = load_last_data()
    print("โหลดข้อมูลเก่า:", last_data)

    html = fetch_page(url)
    data = parse_data(html)
    print("โหลดข้อมูลใหม่:", data)

    notify = False
    reasons = []

    # 1) เปรียบเทียบ diff ขึ้น/ลง ≥ threshold
    diff = data["water_level"] - last_data.get("water_level", 0.0)
    if abs(diff) >= NOTIFICATION_THRESHOLD:
        notify = True
        reasons.append(
            f"ระดับน้ำ{'ขึ้น' if diff>0 else 'ลง'} {abs(diff)*100:.0f} ซม."
            " (เทียบกับครั้งล่าสุดที่ตรวจวัด)"
        )

    # 2) เตือนเมื่อตรวจพบเหตุการณ์ใหม่ (เวลาเปลี่ยน)
    if last_data.get("time") and data["time"] != last_data["time"]:
        notify = True
        reasons.append("เหตุการณ์ใหม่")

    # 3) เตือนเมื่อใกล้ตลิ่งหรือสูงกว่าตลิ่ง
    if data["below_bank"] < 0:
        notify = True
        reasons.append(f"สูงกว่าตลิ่ง {abs(data['below_bank']):.2f} ม.")
    elif data["below_bank"] <= NEAR_BANK_THRESHOLD:
        notify = True
        reasons.append(f"ระดับน้ำใกล้ตลิ่ง ({data['below_bank']:.2f} ม.)")

    if notify:
        # สร้างข้อความแจ้งเตือน
        diff_symbol = '+' if diff >= 0 else '–'
        trend_text  = f"น้ำ{'ขึ้น' if diff>0 else 'ลง'}"
        status_emoji = '🔴' if data['below_bank']<0 else '⚠️' if data['below_bank']<=NEAR_BANK_THRESHOLD else '✅'
        status_text = data['status']
        distance_text = (
            f"{'ต่ำกว่า' if data['below_bank']>0 else 'สูงกว่'}ตลิ่ง {abs(data['below_bank']):.2f} ม."
        )

        message = (
            f"💧 **รายงานระดับน้ำ {data['station_name']}**\n"
            f"🌊 ระดับปัจจุบัน: *{data['water_level']:.2f}* ม.รทก.\n"
            f"⬅️ เดิม: *{last_data.get('water_level', data['water_level']):.2f}* ม.รทก.\n"
            f"📈 แนวโน้ม: *{trend_text}* {diff_symbol}{abs(diff):.2f} ม.\n"
            f"📊 สถานะ: {status_emoji} *{status_text}* ({distance_text})\n"
            f"⏰ ณ: {data['time']}\n"
            f"▶️ เหตุผล: {', '.join(reasons)}"
        )

        print(message)
        send_line_message(message)

        # เก็บข้อมูลใหม่
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print("--> ข้ามการแจ้งเตือน รอบนี้")

    print("--- จบ script ---")


if __name__ == "__main__":
    main()
