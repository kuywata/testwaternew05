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


DATA_FILE = "inburi_bridge_data.json"

# อ่าน threshold
_raw = os.getenv("NOTIFICATION_THRESHOLD_M", "")
try:
    NOTIFICATION_THRESHOLD = float(_raw) if _raw else 0.10
except ValueError:
    print(f"--> ❗ WARN: NOTIFICATION_THRESHOLD_M='{_raw}' แปลงไม่สำเร็จ, ใช้ default=0.10")
    NOTIFICATION_THRESHOLD = 0.10

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
    """ใช้ Selenium รัน headless Chrome รอให้ <th scope='row'> ปรากฏ แล้วคืน page_source"""
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
        text = th.get_text(strip=True)
        if "อินทร์บุรี" in text:
            row = th.find_parent("tr")
            cols = row.find_all("td")
            # ตำบล/อำเภอ = cols[0], water=cols[1], bank=cols[2], status span, below calc, time=cols[6]
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
    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            last_data = json.load(f)
        print("โหลดข้อมูลเก่า:", last_data)

    data = get_water_data()
    if not data:
        print("--> ไม่มีข้อมูลใหม่, จบการทำงาน")
        return

    if last_data.get("water_level") != data["water_level"]:
        msg = (
            f"🌊 สถานี {data['station_name']}:\n"
            f"• ระดับน้ำ: {data['water_level']} ม.\n"
            f"• ระดับตลิ่ง: {data['bank_level']} ม.\n"
            f"• สถานะ: {data['status']}\n"
            f"• ห่างจากตลิ่ง: {data['below_bank']} ม.\n"
            f"🕒 รายงานเวลา: {data['time']}"
        )
        print(msg)
        send_line_message(msg)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print("--> ระดับน้ำไม่เปลี่ยน แสดงว่าไม่ต้องแจ้งเตือน")
    print("--- จบ script ---")


if __name__ == "__main__":
    main()
