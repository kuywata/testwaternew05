import os
import json
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ชื่อไฟล์ที่เก็บข้อมูลครั้งล่าสุด
DATA_FILE = "inburi_bridge_data.json"

# อ่านเกณฑ์จาก ENV (หน่วยเมตร) ถ้าไม่กำหนดจะใช้ 0.10 ม.
NOTIFICATION_THRESHOLD = float(os.getenv("NOTIFICATION_THRESHOLD_M", "0.10"))

# อ่าน LINE token จาก GitHub Secret
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")


def send_line_message(message: str):
    """ส่งข้อความไปที่ LINE via broadcast"""
    if not LINE_ACCESS_TOKEN:
        print("--> ❌ LINE_CHANNEL_ACCESS_TOKEN ไม่ถูกตั้งค่า!")
        return

    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"messages": [{"type": "text", "text": message}]}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            print("--> ✅ ส่ง LINE สำเร็จ")
        else:
            print(f"--> ❌ LINE API error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"--> ❌ Exception when sending LINE: {e}")


def setup_driver():
    """ตั้งค่า headless Chrome สำหรับ Selenium"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # ถ้า path ของ chromium ไม่ตรง ให้ตั้ง ENV CHROME_BIN ให้ชี้ไป /usr/bin/chromium-browser
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def get_water_data():
    """ดึงข้อมูลระดับน้ำจากเว็บ singburi.thaiwater.net"""
    driver = setup_driver()
    try:
        driver.get("https://singburi.thaiwater.net/wl")
        print("--> รอโหลดหน้าเว็บ 7 วินาที...")
        time.sleep(7)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        for row in soup.find_all("tr"):
            th = row.find("th")
            if th and "อินทร์บุรี" in th.text:
                tds = row.find_all("td")
                if len(tds) < 8:
                    continue

                station    = th.text.strip()
                water_lvl  = float(tds[1].text.strip())
                bank_lvl   = float(tds[2].text.strip())
                status     = tds[3].text.strip()
                below_bank = float(tds[4].find_all("div")[1].text.strip())
                timestamp  = tds[6].text.strip()

                return {
                    "station_name": station,
                    "water_level": water_lvl,
                    "bank_level": bank_lvl,
                    "status": status,
                    "below_bank": below_bank,
                    "time": timestamp
                }

        print("--> ❌ ไม่พบสถานี 'อินทร์บุรี' ในตาราง")
        return None

    except Exception as e:
        print(f"--> ❌ Error ดึงข้อมูล: {e}")
        return None

    finally:
        driver.quit()


def main():
    print("--- เริ่มทำงาน inburi_bridge_alert.py ---")

    # โหลดข้อมูลเก่า (ถ้ามี)
    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            last_data = json.load(f)
            print(f"โหลดข้อมูลเก่า: {last_data}")

    # ดึงข้อมูลปัจจุบัน
    data = get_water_data()
    if not data:
        print("--> ไม่มีข้อมูลใหม่, จบการทำงาน")
        return

    # เช็คเงื่อนไขการแจ้งเตือน
    notify = False
    reasons = []

    # ครั้งแรก vs เปลี่ยนเกิน threshold
    if "water_level" not in last_data:
        notify = True
        reasons.append("แจ้งครั้งแรก")
    else:
        diff = abs(data["water_level"] - last_data["water_level"])
        if diff >= NOTIFICATION_THRESHOLD:
            notify = True
            reasons.append(f"ระดับน้ำเปลี่ยน {diff*100:.0f} ซม.")

        last_crit = any(k in last_data.get("status","") for k in ["สูง","ล้น","วิกฤต"])
        curr_crit = any(k in data["status"] for k in ["สูง","ล้น","วิกฤต"])
        if curr_crit and not last_crit:
            notify = True
            reasons.append("สถานะเปลี่ยนเป็นวิกฤต")

    if not reasons:
        reasons.append("การเปลี่ยนแปลงไม่ถึงเกณฑ์")

    print("ผลการเช็ค:", reasons)

    # ส่ง LINE ถ้าต้องแจ้งเตือน
    if notify:
        icon = "🚨" if any(k in data["status"] for k in ["สูง","ล้น","วิกฤต"]) else "💧"
        level_info = (
            f"สูงกว่าตลิ่งอยู่ {abs(data['below_bank']):.2f} เมตร"
            if icon == "🚨"
            else f"ต่ำกว่าตลิ่งอยู่ {data['below_bank']:.2f} เมตร"
        )

        message = (
            f"{icon} **รายงานระดับน้ำแม่น้ำเจ้าพระยา**\n"
            f"📍 สถานี: {data['station_name']}\n"
            f"🗓️ เวลา: {data['time']}\n"
            f"---------------------------------\n"
            f"🌊 ระดับน้ำปัจจุบัน: **{data['water_level']:.2f} ม.รทก.**\n"
            f"〰️ ระดับตลิ่ง: {data['bank_level']:.2f} ม.รทก.\n\n"
            f"📊 **สรุป: {data['status']}** ({level_info})"
        )

        print(message)
        send_line_message(message)

        # บันทึกข้อมูลปัจจุบัน
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print("--> ข้ามการแจ้งเตือน รอบนี้")

    print("--- จบ script ---")


if __name__ == "__main__":
    main()
