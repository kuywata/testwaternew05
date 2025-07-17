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
    chrome_options = Options()
    chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/chromium-browser")
    chrome_options.binary_location = chrome_bin
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_water_data():
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
                if len(tds) < 8: continue
                return {
                    "station_name": th.text.strip(),
                    "water_level": float(tds[1].text.strip()),
                    "bank_level": float(tds[2].text.strip()),
                    "status": tds[3].text.strip(),
                    "below_bank": float(tds[4].find_all("div")[1].text.strip()),
                    "time": tds[6].text.strip()
                }
        print("--> ❌ ไม่พบสถานี 'อินทร์บุรี' ในตาราง")
        return None
    except Exception as e:
        print(f"--> ❌ Error ดึงข้อมูล: {e}")
        return None
    finally:
        driver.quit()

# --- ส่วนนี้เหมือนเดิม ---
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

    notify = False
    reasons = []
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

    if notify:
        # --- ############################################################### ---
        # --- ### ส่วนที่แก้ไข: เพิ่มการแสดงระดับน้ำเดิมและปรับรูปแบบ ### ---
        # --- ############################################################### ---
        
        is_critical = any(k in data["status"] for k in ["สูง","ล้น","วิกฤต"])
        
        if is_critical:
            icon = "🚨"
            summary_text = f"สูงกว่าตลิ่งอยู่ *{abs(data['below_bank']):.2f}* ม."
        else:
            icon = "✅"
            summary_text = f"ต่ำกว่าตลิ่งอยู่ *{data['below_bank']:.2f}* ม."
        
        # สร้างข้อความเปรียบเทียบและแนวโน้ม
        comparison_text = ""
        if "water_level" in last_data:
            level_diff = data["water_level"] - last_data["water_level"]
            trend_icon = "📈" if level_diff > 0 else "📉" if level_diff < 0 else "↔️"
            trend_sign = "+" if level_diff > 0 else ""
            
            comparison_text = (
                f"⬅️ ระดับน้ำเดิม: *{last_data['water_level']:.2f}* ม.รทก.\n\n"
                f"{trend_icon} แนวโน้ม: *น้ำ{'ขึ้น' if level_diff > 0 else 'ลง' if level_diff < 0 else 'คงที่'}* ({trend_sign}{level_diff:.2f} ม.)"
            )
        
        # สร้างข้อความฉบับสมบูรณ์
        message = (
            f"💧 **รายงานระดับน้ำ**\n"
            f"📍 สถานี: {data['station_name']}\n"
            f"──────────────────\n"
            f"🌊 ระดับน้ำปัจจุบัน: *{data['water_level']:.2f}* ม.รทก.\n"
            f"{comparison_text}\n\n"
            f"📊 สถานะ: {icon} *{data['status']}*\n"
            f"       ({summary_text})\n"
            f"──────────────────\n"
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

