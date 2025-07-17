import os
import json
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- ส่วนนี้เหมือนเดิม ---
DATA_FILE = "inburi_bridge_data.json"
NOTIFICATION_THRESHOLD = float(os.getenv("NOTIFICATION_THRESHOLD_M", "0.10"))
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

def send_line_message(message: str):
    if not LINE_ACCESS_TOKEN:
        print("--> ❌ LINE_CHANNEL_ACCESS_TOKEN ไม่ถูกตั้งค่า!")
        return
    # ... (โค้ดส่งข้อความผ่าน LINE API)


def setup_driver():
    from selenium.webdriver.chrome.service import Service
    chrome_options = Options()
    # ชี้ไปที่ไบนารีของ Chromium ที่ติดตั้งด้วย apt
    chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/chromium-browser")
    chrome_options.binary_location = chrome_bin
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # ระบุ path ของ chromedriver ที่ติดตั้งด้วย apt
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def get_water_data():
    driver = setup_driver()
    try:
        driver.get("https://singburi.thaiwater.net/wl")
        print("--> รอโหลดหน้าเว็บ 7 วินาที...")
        time.sleep(7)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # ... (โค้ดดึงข้อมูลน้ำจากตาราง)
        # ตัวอย่าง:
        table = soup.find("table", {"class": "table table-striped"})
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue
            th = row.find("th")
            if th and "อินทร์บุรี" in th.text:
                # แปลงข้อมูลแต่ละคอลัมน์เป็นตัวเลข
                water_level = float(cols[1].text.strip())
                bank_level = float(cols[2].text.strip())
                status = cols[3].text.strip()
                # ... (โค้ดคำนวณ below_bank, time)
                below_bank = bank_level - water_level
                current_time = time.strftime("%H:%M น.", time.localtime())
                data = {
                    "station_name": "อินทร์บุรี",
                    "water_level": water_level,
                    "bank_level": bank_level,
                    "status": status,
                    "below_bank": below_bank,
                    "time": current_time,
                }
                return data
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

    # ตรวจสอบเงื่อนไขการแจ้งเตือน
    if last_data.get("water_level") != data["water_level"]:
        # สร้างข้อความแจ้งเตือน
        message = (
            f"🌊 สถานี {data['station_name']}: ระดับน้ำ {data['water_level']} ม.เหนือระดับน้ำท่วม\n"
            f"🛤️ ระดับตลิ่ง {data['bank_level']} ม.เหนือระดับน้ำท่วม\n"
            f"⚠️ สถานะ: {data['status']}\n"
            f"📉 ห่างจากตลิ่ง {data['below_bank']} ม.\n"
            f"🗓️ ข้อมูล ณ เวลา: {data['time']}"
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
