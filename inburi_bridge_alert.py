# inburi_bridge_alert.py
import os
import json
import time
import requests
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configurations ---
DATA_FILE = "inburi_bridge_data.json"

# อ่าน threshold จาก env (หน่วยเป็นเมตร; default=0.1 ม.)
_raw = os.getenv("NOTIFICATION_THRESHOLD_M", "")
try:
    NOTIFICATION_THRESHOLD = float(_raw) if _raw else 0.1
except ValueError:
    print(f"--> ❗ WARN: NOTIFICATION_THRESHOLD_M='{_raw}' แปลงไม่สำเร็จ, ใช้ default=0.1")
    NOTIFICATION_THRESHOLD = 0.1

LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_TARGET_ID    = os.getenv("LINE_TARGET_ID")


def send_line_message(message: str):
    if not (LINE_ACCESS_TOKEN and LINE_TARGET_ID):
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


def fetch_rendered_html(url: str, timeout: int = 15) -> str:
    """ใช้ Selenium รัน headless Chrome และรอให้ตารางโหลดครบก่อนคืน page_source"""
    chrome_opts = Options()
    chrome_opts.add_argument("--headless")
    chrome_opts.add_argument("--disable-gpu")
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
        print("--> ⚠️ Selenium: รอ element แล้ว timeout")
    html = driver.page_source
    driver.quit()
    return html


def get_water_data():
    url = "https://singburi.thaiwater.net/wl"
    html = fetch_rendered_html(url)
    soup = BeautifulSoup(html, "html.parser")

    for th in soup.find_all("th", {"scope": "row"}):
        if "อินทร์บุรี" in th.get_text(strip=True):
            row = th.find_parent("tr")
            cols = row.find_all("td")
            water_level = float(cols[1].get_text(strip=True))
            bank_level  = float(cols[2].get_text(strip=True))
            status      = row.find("span", class_="badge").get_text(strip=True)
            below_bank  = round(bank_level - water_level, 2)
            report_time = cols[6].get_text(strip=True)
            return {
                "station_name": "อินทร์บุรี",
                "water_level":   water_level,
                "bank_level":    bank_level,
                "status":        status,
                "below_bank":    below_bank,
                "time":          report_time,
            }

    print("--> ไม่เจอข้อมูลสถานี อินทร์บุรี")
    return None


def main():
    print("--- เริ่มทำงาน inburi_bridge_alert.py ---")

    # โหลดข้อมูลเก่า (ถ้ามี)
    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            last_data = json.load(f)
        print("โหลดข้อมูลเก่า:", last_data)

    data = get_water_data()
    if not data:
        print("--> ไม่มีข้อมูลใหม่, จบการทำงาน")
        return

    prev = last_data.get("water_level")
    if prev is None:
        # ครั้งแรก: บันทึกแต่ไม่แจ้ง
        print("--> ยังไม่มีข้อมูลเก่า, บันทึกและไม่แจ้งครั้งแรก")
        to_notify = False
        diff = 0
        direction = ""
    else:
        diff = data["water_level"] - prev
        if abs(diff) >= NOTIFICATION_THRESHOLD:
            direction = "⬆️" if diff > 0 else "⬇️"
            print(f"--> เปลี่ยนแปลง {direction}{abs(diff):.2f} ม. (เกิน {NOTIFICATION_THRESHOLD} ม.)")
            to_notify = True
        else:
            print(f"--> การเปลี่ยนแปลง {diff:.2f} ม. น้อยกว่า {NOTIFICATION_THRESHOLD} ม., ไม่แจ้ง")
            to_notify = False

    if to_notify:
        # ข้อความสวยงามบนมือถือ
        msg = (
            f"📢 แจ้งเตือนระดับน้ำ {direction}{abs(diff):.2f} ม.\n"
            "════════════════════\n"
            f"🌊 ระดับน้ำ     : {data['water_level']} ม.\n"
            f"🏞️ ระดับตลิ่ง    : {data['bank_level']} ม.\n"
            f"🚦 สถานะ       : {data['status']}\n"
            f"📐 ห่างจากตลิ่ง : {data['below_bank']} ม.\n"
            "───────────────\n"
            f"🕒 เวลา        : {data['time']}"
        )
        send_line_message(msg)
        # บันทึกข้อมูลใหม่ทับของเก่า
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print("--> ไม่ต้องแจ้งเตือนครั้งนี้")

    print("--- จบ script ---")


if __name__ == "__main__":
    main()
