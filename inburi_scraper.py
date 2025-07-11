import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import pytz

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
# 🎯 (แก้ไข) ลบบรรทัด import ที่ผิดพลาดออกไปแล้ว

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

# --- การตั้งค่าสำหรับสคริปต์นี้โดยเฉพาะ ---
STATION_URL = "https://singburi.thaiwater.net/wl"
LAST_DATA_FILE = 'last_inburi_data.txt'
STATION_ID_TO_FIND = "C.35"

# --- เกณฑ์การแจ้งเตือน ---
NOTIFICATION_THRESHOLD_METERS = 0.20

def get_inburi_river_data():
    """ดึงข้อมูลระดับน้ำโดยใช้ Selenium เพื่อรอ JavaScript โหลดข้อมูล"""
    print("Setting up Selenium Chrome driver with Eager Page Load Strategy...")
    options = webdriver.ChromeOptions()
    # กำหนดกลยุทธ์การโหลดหน้าเว็บเป็น 'eager' ซึ่งไม่ต้อง import อะไรเพิ่มเติม
    options.page_load_strategy = 'eager'
    
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"Fetching data from {STATION_URL} with Eager strategy...")
        driver.get(STATION_URL)
        
        print("Page is interactive. Now waiting for the specific data table...")
        wait = WebDriverWait(driver, 30) 
        wait.until(EC.presence_of_element_located((By.ID, 'tele_wl')))
        
        print("Table found! Parsing data...")
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')

        table = soup.find('table', id='tele_wl')
        if not table:
            print("Something went wrong, table with id 'tele_wl' not found.")
            return None

        target_row = None
        for row in table.find('tbody').find_all('tr'):
            columns = row.find_all('td')
            if columns and STATION_ID_TO_FIND in columns[0].text:
                target_row = columns
                break
        
        if not target_row:
            print(f"Could not find station {STATION_ID_TO_FIND} in the table.")
            return None

        station_name = target_row[0].text.strip()
        water_level_str = target_row[2].text.strip()
        bank_level_str = target_row[3].text.strip()

        print(f"Found station: {station_name}")
        print(f"  - Water Level: {water_level_str} m.")
        print(f"  - Bank Level: {bank_level_str} m.")

        water_level = float(water_level_str)
        bank_level = float(bank_level_str)
        overflow = water_level - bank_level

        return {
            "station": station_name,
            "water_level": water_level,
            "bank_level": bank_level,
            "overflow": overflow
        }

    except Exception as e:
        print(f"An error occurred in get_inburi_river_data: {e}")
        return None
    finally:
        print("Closing Selenium driver.")
        driver.quit()

def send_line_message(data, change_amount):
    """ส่งข้อความไปยัง LINE พร้อมระบุการเปลี่ยนแปลง"""
    now_thailand = datetime.now(TIMEZONE_THAILAND)
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M น.")
    
    change_direction_icon = "⬆️" if change_amount > 0 else "⬇️"
    change_text = f"เปลี่ยนแปลง {change_direction_icon} {abs(change_amount):.2f} ม."
    
    if data['overflow'] > 0:
        status_text, status_icon, overflow_text = "⚠️ *น้ำล้น
