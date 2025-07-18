#!/usr/bin/env python3
import os
import json
import requests
from bs4 import BeautifulSoup

# Selenium imports for JS‐rendered table
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------- Configurations & Flags --------
DATA_FILE         = "inburi_bridge_data.json"
DEFAULT_THRESHOLD = 0.1  # ม. (10 ซม.)

# ENV‑flags
DRY_RUN        = os.getenv("DRY_RUN", "").lower() in ("1", "true")
USE_LOCAL_HTML = os.getenv("USE_LOCAL_HTML", "").lower() in ("1", "true")
LOCAL_HTML     = os.getenv("LOCAL_HTML_PATH", "page.html")

# Read threshold from env (meters)
_raw = os.getenv("NOTIFICATION_THRESHOLD_M", "")
try:
    NOTIFICATION_THRESHOLD = float(_raw) if _raw else DEFAULT_THRESHOLD
except ValueError:
    print(f"[WARN] แปลง NOTIFICATION_THRESHOLD_M='{_raw}' ไม่สำเร็จ → ใช้ default={DEFAULT_THRESHOLD}")
    NOTIFICATION_THRESHOLD = DEFAULT_THRESHOLD

LINE_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_TARGET = os.getenv("LINE_TARGET_ID")


def send_line_message(msg: str):
    """ส่งข้อความผ่าน LINE Messaging API"""
    if DRY_RUN:
        print("[DRY‑RUN] send_line_message() ➔")
        print(msg)
        return

    if not (LINE_TOKEN and LINE_TARGET):
        print("[ERROR] LINE_TOKEN/LINE_TARGET ไม่ครบ!")
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type":  "application/json"
    }
    payload = {
        "to": LINE_TARGET,
        "messages": [{"type": "text", "text": msg}]
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.status_code != 200:
        print(f"[ERROR] ส่ง LINE ล้มเหลว: {resp.status_code} {resp.text}")


def fetch_rendered_html(url, timeout=15) -> str:
    """โหลดหน้าเว็บด้วย Selenium หรือจากไฟล์ local (mock)"""
    if USE_LOCAL_HTML:
        print(f"[INFO] USE_LOCAL_HTML=TRUE, อ่านจากไฟล์ {LOCAL_HTML}")
        with open(LOCAL_HTML, "r", encoding="utf-8") as f:
            return f.read()

    chrome_opts = Options()
    chrome_opts.add_argument("--headless")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_opts
    )
    driver.get(url)
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "th[scope='row']"))
        )
    except Exception:
        print("[WARN] Selenium timeout รอ table JS")
    html = driver.page_source
    driver.quit()
    return html


def get_water_data():
    """Parse ข้อมูลสถานี อินทร์บุรี จาก HTML"""
    print("[DEBUG] ดึง HTML จากเว็บ...")
    html = fetch_rendered_html("https://singburi.thaiwater.net/wl")
    print(f"[DEBUG] HTML length = {len(html)} chars")

    soup = BeautifulSoup(html, "html.parser")
    for th in soup.select("th[scope='row']"):
        txt = th.get_text(strip=True)
        if "อินทร์บุรี" in txt:
            tr   = th.find_parent("tr")
            cols = tr.find_all("td")
            water_level = float(cols[1].get_text(strip=True))
            bank_level  = float(cols[2].get_text(strip=True))
            status      = tr.select_one("span.badge").get_text(strip=True)
            below_bank  = round(bank_level - water_level, 2)
            report_time = cols[6].get_text(strip=True)

            print(f"[DEBUG] Parsed water={water_level}, bank={bank_level}, status={status}, below={below_bank}, time={report_time}")
            return {
                "station_name": "อินทร์บุรี",
                "water_level":   water_level,
                "bank_level":    bank_level,
                "status":        status,
                "below_bank":    below_bank,
                "time":          report_time,
            }

    print("[ERROR] ไม่พบข้อมูลสถานี อินทร์บุรี ใน HTML")
    return None


def main():
    print("=== เริ่ม inburi_bridge_alert ===")
    # โหลดข้อมูลเก่า
    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            last_data = json.load(f)
        print(f"[DEBUG] last_data = {last_data}")

    data = get_water_data()
    if not data:
        return

    prev = last_data.get("water_level")
    if prev is None:
        print("[INFO] ไม่มีข้อมูลเก่า, บันทึกแต่ไม่แจ้งครั้งแรก")
        need_alert = False
        diff       = 0.0
        direction  = ""
    else:
        diff = data["water_level"] - prev
        print(f"[DEBUG] diff = {diff:.2f} (threshold={NOTIFICATION_THRESHOLD})")
        if abs(diff) >= NOTIFICATION_THRESHOLD:
            direction = "⬆️" if diff > 0 else "⬇️"
            need_alert = True
        else:
            print("[INFO] diff น้อยกว่า threshold, ไม่แจ้ง")
            need_alert = False

    # สร้างข้อความและส่ง (หรือ dry‑run)
    if need_alert:
        msg = (
            f"📢 แจ้งระดับน้ำ {direction}{abs(diff):.2f} ม. (อินทร์บุรี)\n"
            "══════════════════\n"
            f"🌊 ระดับน้ำ     : {data['water_level']} ม.\n"
            f"🏞️ ระดับตลิ่ง    : {data['bank_level']} ม.\n"
            f"🚦 สถานะ       : {data['status']}\n"
            f"📐 ห่างจากตลิ่ง : {data['below_bank']} ม.\n"
            "───────────────\n"
            f"🕒 เวลา        : {data['time']}"
        )
        send_line_message(msg)
    else:
        print("[INFO] ไม่มีการแจ้งเตือนในรอบนี้")

    # บันทึกข้อมูลใหม่เสมอ ไม่ว่าจะ alert หรือไม่
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("=== จบ inburi_bridge_alert ===")


if __name__ == "__main__":
    main()
