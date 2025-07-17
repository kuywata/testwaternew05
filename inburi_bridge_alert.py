#!/usr/bin/env python3
import os
import json
import time
import requests
import shutil
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# --- Configuration ---
DATA_FILE               = "inburi_bridge_data.json"
NOTIFICATION_THRESHOLD  = float(os.getenv("NOTIFICATION_THRESHOLD_M", "0.10"))  # 10 cm
NEAR_BANK_THRESHOLD     = float(os.getenv("NEAR_BANK_THRESHOLD_M",    "1.0"))   # 1 m
LINE_ACCESS_TOKEN       = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL            = "https://api.line.me/v2/bot/message/broadcast"
TARGET_URL              = "https://waterdata.dwr.go.th/river-level/"  # ปรับ URL ให้ตรงกับต้นทางจริง

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium-browser")

    chromedriver_path = shutil.which("chromedriver") or os.getenv("CHROMEDRIVER_PATH")
    service = Service(chromedriver_path) if chromedriver_path else Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def fetch_page(url):
    driver = setup_driver()
    try:
        driver.get(url)
        time.sleep(7)
        return driver.page_source
    finally:
        driver.quit()

def parse_data(html):
    soup = BeautifulSoup(html, "html.parser")

    # 1) station_name
    station_elem = soup.select_one(".station-title")
    if not station_elem:
        raise ValueError("ไม่พบ .station-title")
    station_name = station_elem.get_text(strip=True)

    # 2) water_level
    wl_elem = soup.select_one("#waterLevel")
    if not wl_elem:
        raise ValueError("ไม่พบ #waterLevel")
    water_level = float(re.search(r"[\d\.]+", wl_elem.get_text()).group())

    # 3) bank_level
    bank_elem = soup.select_one("#bankLevel")
    if not bank_elem:
        raise ValueError("ไม่พบ #bankLevel")
    bank_level = float(re.search(r"[\d\.]+", bank_elem.get_text()).group())

    # 4) below_bank and status
    below_bank = bank_level - water_level
    status     = "น้ำปกติ" if water_level < bank_level else "วิกฤต"

    # 5) timestamp
    time_elem = soup.select_one(".updated-time")
    if not time_elem:
        raise ValueError("ไม่พบ .updated-time")
    timestamp = time_elem.get_text(strip=True)

    return {
        "station_name": station_name,
        "water_level":  water_level,
        "bank_level":   bank_level,
        "below_bank":   below_bank,
        "status":       status,
        "time":         timestamp
    }

def load_last_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"station_name":"อินทร์บุรี","water_level":0.0,"bank_level":0.0,"below_bank":0.0,"status":"","time":""}

def send_line_message(text):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {LINE_ACCESS_TOKEN}"}
    payload = {"messages":[{"type":"text","text":text}]}
    resp = requests.post(LINE_API_URL, headers=headers, json=payload)
    if resp.status_code == 200:
        print("--> ✅ ส่ง LINE สำเร็จ")
    else:
        print(f"--> ❌ ส่ง LINE ล้มเหลว: {resp.status_code} {resp.text}")

def main():
    print(f"--- เริ่มทำงาน {__file__} ---")
    last_data = load_last_data()
    print("โหลดข้อมูลเก่า:", last_data)

    html = fetch_page(TARGET_URL)
    try:
        data = parse_data(html)
    except Exception as e:
        print(f"--> ❌ เกิดข้อผิดพลาดตอนอ่านข้อมูลจากหน้าเว็บ: {e}")
        # บันทึก snapshot ไว้ดีบัก
        with open("snapshot.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("--> บันทึก snapshot.html สำหรับตรวจสอบโครงสร้างหน้าเว็บ")
        return

    print("โหลดข้อมูลใหม่:", data)
    notify = False
    reasons = []

    diff = data["water_level"] - last_data.get("water_level",0.0)
    if abs(diff) >= NOTIFICATION_THRESHOLD:
        notify = True
        reasons.append(f"ระดับน้ำ{'ขึ้น' if diff>0 else 'ลง'} {abs(diff)*100:.0f} ซม. (เทียบกับครั้งล่าสุด)")

    if last_data.get("time") and data["time"] != last_data["time"]:
        notify = True
        reasons.append("เหตุการณ์ใหม่")

    if data["below_bank"] < 0:
        notify = True
        reasons.append(f"สูงกว่าตลิ่ง {abs(data['below_bank']):.2f} ม.")
    elif data["below_bank"] <= NEAR_BANK_THRESHOLD:
        notify = True
        reasons.append(f"ระดับน้ำใกล้ตลิ่ง ({data['below_bank']:.2f} ม.)")

    if notify:
        trend = f"น้ำ{'ขึ้น' if diff>0 else 'ลง'}"
        sym   = '+' if diff>=0 else '–'
        emo   = '🔴' if data['below_bank']<0 else '⚠️' if data['below_bank']<=NEAR_BANK_THRESHOLD else '✅'
        dist  = f"{'ต่ำกว่า' if data['below_bank']>0 else 'สูงกว่'}ตลิ่ง {abs(data['below_bank']):.2f} ม."
        msg = (
            f"💧 **รายงานระดับน้ำ {data['station_name']}**\n"
            f"🌊 ระดับปัจจุบัน: *{data['water_level']:.2f}* ม.รทก.\n"
            f"⬅️ เดิม: *{last_data.get('water_level',data['water_level']):.2f}* ม.รทก.\n"
            f"📈 แนวโน้ม: *{trend}* {sym}{abs(diff):.2f} ม.\n"
            f"📊 สถานะ: {emo} *{data['status']}* ({dist})\n"
            f"⏰ ณ: {data['time']}\n"
            f"▶️ เหตุผล: {', '.join(reasons)}"
        )
        print(msg)
        send_line_message(msg)
        with open(DATA_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
    else:
        print("--> ข้ามการแจ้งเตือน รอบนี้")

    print("--- จบ script ---")

if __name__ == "__main__":
    main()
