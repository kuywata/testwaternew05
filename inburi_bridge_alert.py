import os
import json
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

DATA_FILE = "inburi_bridge_data.json"
NOTIFICATION_THRESHOLD = float(os.getenv("NOTIFICATION_THRESHOLD_M", "0.10"))
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

def send_line_message(message: str):
    if not LINE_ACCESS_TOKEN:
        print("--> ❌ LINE_CHANNEL_ACCESS_TOKEN ไม่ถูกตั้งค่า!")
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": os.getenv("LINE_TARGET_ID"),
        "messages": [{"type": "text", "text": message}]
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        print(f"--> ❌ ส่ง LINE ไม่สำเร็จ: {resp.status_code} {resp.text}")

def setup_driver():
    chrome_options = Options()
    chrome_options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/google-chrome-stable")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(executable_path=os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
    return webdriver.Chrome(service=service, options=chrome_options)

def get_water_data():
    driver = setup_driver()
    try:
        driver.get("https://singburi.thaiwater.net/wl")
        print("--> รอโหลดหน้าเว็บ 7 วินาที...")
        time.sleep(7)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table", {"class": "table table-striped"})
        if not table:
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
    finally:
        driver.quit()

def main():
    print("--- เริ่มทำงาน inburi_bridge_alert.py ---")

    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            last_data = json.load(f)
        print(f"โหลดข้อมูลเก่า: {last_data}")

    data = get_water_data()
    if not data:
        print("--> ไม่มีข้อมูลใหม่, จบการทำงาน")
        return

    if last_data.get("water_level") != data["water_level"]:
        message = (
            f"🌊 สถานี {data['station_name']}:\n"
            f"• ระดับน้ำ: {data['water_level']} ม.เหนือระดับน้ำท่วม\n"
            f"• ระดับตลิ่ง: {data['bank_level']} ม.\n"
            f"• สถานะ: {data['status']}\n"
            f"• ห่างจากตลิ่ง: {data['below_bank']} ม.\n"
            f"🕒 เวลา: {data['time']}"
        )
        print(message)
        send_line_message(message)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print("--> ข้ามการแจ้งเตือน รอบนี้")

    print("--- จบ script ---")

if __name__ == "__main__":
    main()
