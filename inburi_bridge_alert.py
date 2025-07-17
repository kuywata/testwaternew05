import os
import json
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import requests

# --- Constants ---
DATA_FILE = "inburi_bridge_data.json"
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/broadcast"
TARGET_URL = "https://www.thaiwater.net/water/station/inburi/C.2"
NOTIFICATION_THRESHOLD = 0.01  # 1 cm

def get_webdriver():
    """Initializes a headless Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    try:
        # This will automatically download and manage the correct chromedriver
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"--> ERROR setting up WebDriver: {e}")
        return None

def fetch_web_data():
    """Fetches data by scraping the website using Selenium."""
    driver = get_webdriver()
    if not driver:
        return None
        
    try:
        print(f"--> Navigating to {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # Wait explicitly for the data container to be present
        wait = WebDriverWait(driver, 20) # Wait up to 20 seconds
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".station-detail .text-end")))
        print("--> Page and data container loaded.")

        # Extract data using specific selectors
        water_level_element = driver.find_element(By.XPATH, "//div[contains(text(), 'ระดับน้ำล่าสุด')]/following-sibling::div")
        water_level = float(water_level_element.text)
        
        bank_level_element = driver.find_element(By.XPATH, "//div[contains(text(), 'ระดับตลิ่ง')]/following-sibling::div")
        bank_level = float(bank_level_element.text)

        time_element = driver.find_element(By.XPATH, "//div[contains(text(), 'ข้อมูลล่าสุด')]/following-sibling::div")
        timestamp = time_element.text.strip()
        
        status_element = driver.find_element(By.XPATH, "//div[contains(text(), 'สถานการณ์')]/following-sibling::div")
        status = status_element.text.strip()

        return {
            "station_name": "สถานีอินทร์บุรี (C.2)", "water_level": water_level,
            "bank_level": bank_level, "below_bank": bank_level - water_level,
            "status": status, "time": timestamp
        }
    except Exception as e:
        print(f"--> ERROR during scraping: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def send_line_message(text):
    if not LINE_ACCESS_TOKEN:
        return
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messages": [{"type": "text", "text": text}]}
    try:
        requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
        print("--> LINE Sent Successfully.")
    except Exception as e:
        print(f"--> LINE Send ERROR: {e}")

def main():
    print("--- Running Final Scraper Script ---")
    last_data = json.load(open(DATA_FILE)) if os.path.exists(DATA_FILE) else {}
    print(f"Old Data Level: {last_data.get('water_level', 'None')}")
    
    data = fetch_web_data()
    if not data:
        print("--- EXIT: Could not fetch new data. ---")
        return
    print(f"New Data Level: {data['water_level']}")

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not last_data or data["time"] == last_data.get("time"):
        print("--> Data is unchanged or first run. No notification needed.")
        return

    diff = data["water_level"] - last_data.get("water_level", 0.0)
    if abs(diff) < NOTIFICATION_THRESHOLD:
        print(f"--> No significant change ({diff:.3f}m). No notification.")
        return

    trend_text = f"น้ำ{'ขึ้น' if diff > 0 else 'ลง'}"
    status_emoji = '🔴' if 'ล้นตลิ่ง' in data['status'] else '⚠️' if 'เฝ้าระวัง' in data['status'] else '✅'
    
    message = ( f"💧 รายงานระดับน้ำ {data['station_name']}\n\n"
                f"🌊 ระดับปัจจุบัน: {data['water_level']:.2f} ม.รทก. ({trend_text})\n\n"
                f"📊 สถานะ: {status_emoji} {data['status']}\n\n"
                f"⏰ เวลา: {data['time']}")
    
    print("--- Change detected! Sending LINE message. ---")
    send_line_message(message)
    print("--- Script Finished ---")

if __name__ == "__main__":
    main()
