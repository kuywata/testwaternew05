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
STATION_TYPE            = "waterlevel"
STATION_ID              = "C.2"
# ใช้ path กลาง thaiwater30 ตามตัวอย่าง rain_24h API
API_BASE                = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public"
API_URL                 = (
    f"{API_BASE}/tele_station_data"
    f"?station_type={STATION_TYPE}&station_id={STATION_ID}"
)
TARGET_URL              = "https://waterdata.dwr.go.th/river-level/"  # fallback scraping

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium-browser")

    driver_path = shutil.which("chromedriver") or os.getenv("CHROMEDRIVER_PATH")
    service = Service(driver_path) if driver_path else Service()
    return webdriver.Chrome(service=service, options=options)

def fetch_html(url):
    driver = setup_driver()
    try:
        driver.get(url)
        time.sleep(7)
        return driver.page_source
    finally:
        driver.quit()

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    station = soup.select_one(".station-title")
    wl      = soup.select_one("#waterLevel")
    bank    = soup.select_one("#bankLevel")
    updt    = soup.select_one(".updated-time")
    if not all((station, wl, bank, updt)):
        raise ValueError("HTML parsing: ไม่พบ element ที่ต้องการ")
    wlevel = float(re.search(r"[\d\.]+", wl.get_text()).group())
    blevel = float(re.search(r"[\d\.]+", bank.get_text()).group())
    return {
        "station_name": station.get_text(strip=True),
        "water_level":  wlevel,
        "bank_level":   blevel,
        "below_bank":   blevel - wlevel,
        "status":       "น้ำปกติ" if wlevel < blevel else "วิกฤต",
        "time":         updt.get_text(strip=True)
    }

def fetch_api():
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    # ตัวอย่าง JSON: {"data":[{"stationName":"อินทร์บุรี","waterLevel":6.43,"bankLevel":15.1,"datetime":"2025-07-17T16:30:00"}]}
    rec = j["data"][0]
    wlevel = float(rec["waterLevel"])
    blevel = float(rec["bankLevel"])
    return {
        "station_name": rec.get("stationName",""),
        "water_level":  wlevel,
        "bank_level":   blevel,
        "below_bank":   blevel - wlevel,
        "status":       "น้ำปกติ" if wlevel < blevel else "วิกฤต",
        "time":         rec.get("datetime","")
    }

def load_last():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    return {"water_level":0.0,"bank_level":0.0,"below_bank":0.0,"time":""}

def send_line(text):
    headers = {
        "Content-Type":"application/json",
        "Authorization":f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {"messages":[{"type":"text","text":text}]}
    r = requests.post(LINE_API_URL, headers=headers, json=payload)
    if r.status_code!=200:
        print(f"LINE Error: {r.status_code} {r.text}")

def main():
    print("--- เริ่ม Script ---")
    last = load_last()
    print("Old Data:", last)

    # 1) ลอง API ก่อน
    try:
        data = fetch_api()
        print("API Data:", data)
    except requests.HTTPError as e:
        print("API 404 หรือ error:", e)
        print("Fallback ไป HTML scraping...")
        html = fetch_html(TARGET_URL)
        data = parse_html(html)
        print("HTML Data:", data)

    diff = data["water_level"] - last.get("water_level",0.0)
    reasons = []
    notify = False

    if abs(diff) >= NOTIFICATION_THRESHOLD:
        notify = True
        reasons.append(f"ระดับน้ำ{'ขึ้น' if diff>0 else 'ลง'} {abs(diff)*100:.0f} ซม.")
    if last.get("time") and data["time"]!= last["time"]:
        notify = True
        reasons.append("เหตุการณ์ใหม่")
    if data["below_bank"]<0:
        notify = True
        reasons.append(f"สูงกว่าตลิ่ง {abs(data['below_bank']):.2f} ม.")
    elif data["below_bank"]<= NEAR_BANK_THRESHOLD:
        notify = True
        reasons.append(f"ใกล้ตลิ่ง {data['below_bank']:.2f} ม.")

    if notify:
        emo = "🔴" if data["below_bank"]<0 else "⚠️" if data["below_bank"]<=NEAR_BANK_THRESHOLD else "✅"
        trend = f"น้ำ{'ขึ้น' if diff>0 else 'ลง'}"
        sym   = '+' if diff>=0 else '–'
        msg = (
            f"💧 รายงานระดับน้ำ {data['station_name']}\n"
            f"🌊 ปัจจุบัน: {data['water_level']:.2f} ม.รทก.\n"
            f"⬅️ ก่อนหน้า: {last.get('water_level',data['water_level']):.2f} ม.รทก.\n"
            f"📈 แนวโน้ม: {trend} {sym}{abs(diff):.2f} ม.\n"
            f"📊 สถานะ: {emo} {data['status']}\n"
            f"⏰ ณ: {data['time']}\n"
            f"▶️ เหตุผล: {', '.join(reasons)}"
        )
        print(msg)
        send_line(msg)
        with open(DATA_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
    else:
        print("ไม่มีการแจ้งเตือน")

    print("--- จบ Script ---")

if __name__=="__main__":
    main()
