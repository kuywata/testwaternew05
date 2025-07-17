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
    options.add_argument("--no-sandbox") # Add this for compatibility in GitHub Actions
    options.add_argument("--disable-dev-shm-usage") # Add this for compatibility
    options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium-browser")
    
    # In GitHub Actions, chromedriver is often in the PATH, so Service() is enough
    driver = webdriver.Chrome(service=Service(), options=options)
    
    html = ""
    try:
        driver.get(url)
        # Wait for the dynamic content to load
        time.sleep(7) 
        html = driver.page_source
    except Exception as e:
        print(f"--> ❌ เกิดข้อผิดพลาดตอนโหลดหน้าเว็บ: {e}")
    finally:
        driver.quit()
        
    return html


def parse_data(html):
    soup = BeautifulSoup(html, "html.parser")
    
    try:
        # New selectors for thaiwater.net
        station_name_raw = soup.select_one("h5.modal-title").text.strip() # "สถานี C.2 อินทร์บุรี"
        station_name = station_name_raw.replace("สถานี ", "") # "C.2 อินทร์บุรี"
        
        details_div = soup.find("div", id="station_detail_graph")
        
        water_level_label = details_div.find(lambda tag: 'ระดับน้ำล่าสุด' in tag.text)
        water_level = float(water_level_label.find_next_sibling("div").text.strip())

        bank_level_label = details_div.find(lambda tag: 'ระดับตลิ่ง' in tag.text)
        bank_level = float(bank_level_label.find_next_sibling("div").text.strip())
        
        below_bank = bank_level - water_level

        time_label = details_div.find(lambda tag: 'ข้อมูลล่าสุด' in tag.text)
        timestamp = time_label.find_next_sibling("div").text.strip().replace(" น.", "น.")

        status_label = details_div.find(lambda tag: 'สถานการณ์' in tag.text)
        status = status_label.find_next_sibling("div").text.strip()

        return {
            "station_name": station_name,
            "water_level": water_level,
            "bank_level": bank_level,
            "below_bank": below_bank,
            "status": status,
            "time": timestamp
        }
    except Exception as e:
        print(f"--> ❌ เกิดข้อผิดพลาดตอนอ่านข้อมูลจากหน้าเว็บ: {e}")
        print("--> อาจเป็นเพราะหน้าเว็บมีการเปลี่ยนแปลงโครงสร้าง หรือโหลดไม่สำเร็จ")
        return None


def send_line_message(text):
    if not LINE_ACCESS_TOKEN:
        print("--> ⚠️ ไม่ได้ตั้งค่า LINE_CHANNEL_ACCESS_TOKEN ข้ามการส่งข้อความ")
        return
        
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
    # URL for the specific station "C.2 อินทร์บุรี" on the new platform
    url = "https://www.thaiwater.net/water/station/inburi/C.2"
    
    last_data = load_last_data()
    print("โหลดข้อมูลเก่า:", last_data)

    html = fetch_page(url)
    if not html:
        print("--- ไม่สามารถดึงข้อมูลหน้าเว็บได้ จบการทำงาน ---")
        return

    data = parse_data(html)
    if not data:
        print("--- ไม่สามารถอ่านข้อมูลจากหน้าเว็บได้ จบการทำงาน ---")
        return
        
    print("โหลดข้อมูลใหม่:", data)

    notify = False
    reasons = []

    # 1) เปรียบเทียบ diff ขึ้น/ลง ≥ threshold
    diff = data["water_level"] - last_data.get("water_level", 0.0)
    if abs(diff) >= NOTIFICATION_THRESHOLD:
        notify = True
        reasons.append(
            f"ระดับน้ำ{'ขึ้น' if diff>0 else 'ลง'} {abs(diff)*100:.0f} ซม."
        )

    # 2) เตือนเมื่อเวลาของข้อมูลเปลี่ยนไป (เป็นการยืนยันว่ามีข้อมูลใหม่)
    if last_data.get("time") and data["time"] != last_data["time"]:
         # This condition is usually met if there's any change, so let's rely on other reasons for the notification text.
         # We can assume if other conditions are met, it's a new event.
         pass

    # 3) เตือนเมื่อใกล้ตลิ่งหรือสูงกว่าตลิ่ง
    if data["below_bank"] < 0:
        if not any("สูงกว่าตลิ่ง" in r for r in reasons):
             reasons.append(f"สูงกว่าตลิ่ง {abs(data['below_bank']):.2f} ม.")
    elif data["below_bank"] <= NEAR_BANK_THRESHOLD:
        if not any("ใกล้ตลิ่ง" in r for r in reasons):
            reasons.append(f"ใกล้ตลิ่ง ({data['below_bank']:.2f} ม.)")

    # If any reason was added, we should notify.
    if reasons:
        notify = True
        if "ระดับน้ำ" not in reasons[0] : # If the first reason is not the water level change, add a generic "New data" reason
             if data["time"] != last_data.get("time"):
                reasons.insert(0, "มีข้อมูลอัปเดตใหม่")


    if notify:
        # สร้างข้อความแจ้งเตือน
        diff_symbol = '+' if diff >= 0 else ''
        trend_text  = f"น้ำ{'ขึ้น' if diff>0 else 'ลง'}" if diff != 0 else "คงที่"
        status_emoji = '🔴' if 'เฝ้าระวัง' in data['status'] or 'ล้นตลิ่ง' in data['status'] else '⚠️' if 'น้อยวิกฤต' in data['status'] else '✅'
        
        status_text = data['status']
        distance_text = (
            f"{'ต่ำกว่า' if data['below_bank']>=0 else 'สูงกว่า'}ตลิ่ง {abs(data['below_bank']):.2f} ม."
        )

        message = (
            f"💧 รายงานระดับน้ำ {data['station_name']}\n\n"
            f"🌊 ระดับปัจจุบัน: {data['water_level']:.2f} ม.รทก.\n"
            f"({trend_text} {diff_symbol}{abs(diff):.2f} ม.)\n\n"
            f"📊 สถานะ: {status_emoji} {status_text}\n"
            f"({distance_text})\n\n"
            f"⏰ เวลา: {data['time']}\n"
            f"เหตุผลแจ้งเตือน: {', '.join(reasons)}"
        )

        print("--- สร้างข้อความสำหรับส่ง LINE ---")
        print(message)
        send_line_message(message)

        # เก็บข้อมูลใหม่
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"--> ✅ บันทึกข้อมูลใหม่ลงไฟล์ {DATA_FILE}")
    else:
        print("--> ระดับน้ำไม่เปลี่ยนแปลงอย่างมีนัยสำคัญ ข้ามการแจ้งเตือน")

    print("--- จบการทำงาน ---")


if __name__ == "__main__":
    main()
