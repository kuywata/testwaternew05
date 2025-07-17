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
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# --- LINE notification ---
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

# --- WebDriver setup ---
def setup_driver():
    chrome_options = Options()
    # Determine Chrome/Chromium binary location
    chrome_bin = os.getenv("CHROME_BIN")
    if not chrome_bin:
        # try common binaries
        chrome_bin = (
            shutil.which("chromium-browser") or
            shutil.which("chromium") or
            shutil.which("google-chrome") or
            "/usr/bin/google-chrome"
        )
    chrome_options.binary_location = chrome_bin
    # headless mode arguments
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    # Determine chromedriver path
    chromedriver_path = (
        shutil.which("chromedriver") or
        os.getenv("CHROMEDRIVER_PATH")
    )
    if chromedriver_path:
        service = Service(chromedriver_path)
    else:
        service = Service()

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- Data extraction ---
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
                if len(tds) < 8:
                    continue
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

# --- Main workflow ---
def main():
    print("--- เริ่มทำงาน inburi_bridge_alert.py ---")
    last_data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                last_data = json.load(f)
                print(f"โหลดข้อมูลเก่า: {last_data}")
            except json.JSONDecodeError:
                print("--> ⚠️ ไฟล์ข้อมูลเก่าเสีย, เริ่มใหม่")
                last_data = {}

    data = get_water_data()
    if not data:
        print("--> ไม่มีข้อมูลใหม่, จบการทำงาน")
        return

    notify = False
    reasons = []

    # Check for initial run or significant water level change
    if "water_level" not in last_data:
        notify = True
        reasons.append("แจ้งครั้งแรก")
    else:
        diff = abs(data["water_level"] - last_data["water_level"])
        if diff >= NOTIFICATION_THRESHOLD:
            notify = True
            reasons.append(f"ระดับน้ำเปลี่ยน {diff*100:.0f} ซม.")
        
        # Check for change in critical status
        critical_statuses = ["สูง", "ล้น", "วิกฤต"]
        last_crit = any(k in last_data.get("status", "") for k in critical_statuses)
        curr_crit = any(k in data["status"] for k in critical_statuses)

        if curr_crit and not last_crit:
            notify = True
            reasons.append("สถานะเปลี่ยนเป็นวิกฤต")
        elif not curr_crit and last_crit:
            notify = True
            reasons.append("สถานะพ้นวิกฤต")
        # If both are critical or both are not critical, no status change trigger unless water level changes significantly

    if not reasons:
        reasons.append("การเปลี่ยนแปลงไม่ถึงเกณฑ์")

    print("ผลการเช็ค:", reasons)

    if notify:
        is_critical = any(k in data["status"] for k in ["สูง", "ล้น", "วิกฤต"])
        icon = "🚨" if is_critical else "✅"
        
        # Determine summary text based on below_bank value
        summary_text = ""
        if data['below_bank'] < 0: # This means it's above bank level, as below_bank is negative
            summary_text = f"สูงกว่าตลิ่ง *{abs(data['below_bank']):.2f}* ม."
        else:
            summary_text = f"ต่ำกว่าตลิ่ง *{data['below_bank']:.2f}* ม."

        comparison_text = ""
        if "water_level" in last_data:
            level_diff = data["water_level"] - last_data["water_level"]
            trend_icon = "📈" if level_diff > 0 else "📉" if level_diff < 0 else "↔️"
            trend_word = "ขึ้น" if level_diff > 0 else "ลง" if level_diff < 0 else "คงที่"
            
            # Only show numerical change if it's not "คงที่" and is significant
            if level_diff != 0:
                trend_change = f" ({'+' if level_diff > 0 else ''}{level_diff:.2f} ม.)"
            else:
                trend_change = ""

            comparison_text = (
                f"⬅️ เดิม: *{last_data['water_level']:.2f}* ม.รทก.\n"
                f"{trend_icon} แนวโน้ม: *น้ำ{trend_word}*{trend_change}"
            )

        message = (
            f"💧 **รายงานระดับน้ำ อินทร์บุรี**\n"
            f"🌊 ระดับปัจจุบัน: *{data['water_level']:.2f}* ม.รทก.\n"
            f"{comparison_text}\n"
            f"📊 สถานะ: {icon} *{data['status']}* ({summary_text})\n"
            f"⏰ ณ: {data['time']}"
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
