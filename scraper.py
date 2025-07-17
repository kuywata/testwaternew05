import requests
import re
import json
import os
from datetime import datetime, timedelta
import pytz
import time
from bs4 import BeautifulSoup

# --- ค่าคงที่และ URL ---
URL = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')
HISTORICAL_LOG_FILE = 'historical_log.csv'
LAST_DATA_FILE = 'last_data.txt'

# --- ฟังก์ชันดึงข้อมูล (เขียนใหม่ทั้งหมดเพื่อความเสถียรสูงสุด) ---
def get_water_data():
    """
    ดึงข้อมูล "ปริมาณน้ำ" โดยใช้วิธีค้นหาจาก pattern ที่แน่นอนที่สุดใน HTML
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        timestamp = int(time.time())
        url_with_cache_bust = f"{URL}?_={timestamp}"
        response = requests.get(url_with_cache_bust, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # ค้นหาทุก <td> ที่มี class 'text_bold' และ attribute 'colspan' เป็น '2'
        # ซึ่งเป็นลักษณะเฉพาะของช่องข้อมูลที่เราต้องการ
        value_tags = soup.find_all('td', class_='text_bold', colspan='2')
        
        for tag in value_tags:
            # ตรวจสอบว่าใน tag นั้นมีเครื่องหมาย '/' หรือไม่ เพื่อให้แน่ใจว่าเป็นข้อมูลปริมาณน้ำ
            if '/' in tag.get_text():
                raw_text = tag.get_text(strip=True)
                water_value = raw_text.split('/')[0].strip()
                if water_value:
                    return f"{water_value} cms"

        print("Could not find the specific water data tag.")
        return None

    except Exception as e:
        print(f"Error in get_water_data: {e}")
        return None

# --- ฟังก์ชันสำหรับข้อมูลย้อนหลัง (คงเดิม) ---
def get_historical_data(target_date):
    if not os.path.exists(HISTORICAL_LOG_FILE):
        return None
    start_range = target_date - timedelta(hours=12)
    end_range = target_date + timedelta(hours=12)
    closest_entry = None
    smallest_diff = timedelta.max
    with open(HISTORICAL_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                timestamp_str, value = line.strip().split(',', 1)
                log_date = datetime.fromisoformat(timestamp_str)
                if log_date.tzinfo is None:
                    log_date = TIMEZONE_THAILAND.localize(log_date)
                if start_range <= log_date <= end_range:
                    diff = abs(target_date - log_date)
                    if diff < smallest_diff:
                        smallest_diff = diff
                        closest_entry = value
            except ValueError:
                continue
    return closest_entry

def append_to_historical_log(now, data):
    with open(HISTORICAL_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{now.isoformat()},{data}\n")

# --- ฟังก์ชันส่ง LINE (คงเดิม) ---
def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("Missing LINE credentials.")
        return
    url = 'https://api.line.me/v2/bot/message/push'
    headers = { 'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}' }
    payload = { 'to': LINE_TARGET_ID, 'messages': [{'type':'text','text':message}] }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"LINE API Response Status: {response.status_code}")
        print(f"LINE API Response Body: {response.text}")
        response.raise_for_status()
        print("LINE message request sent successfully to LINE API.")
    except Exception as e:
        print(f"An error occurred while sending LINE message: {e}")

# --- การทำงานหลัก (คงเดิม) ---
def main():
    last_data = ''
    if os.path.exists(LAST_DATA_FILE):
        with open(LAST_DATA_FILE, 'r', encoding='utf-8') as f:
            last_data = f.read().strip()
    current_data = get_water_data()
    if current_data:
        print(f"Current data retrieved: {current_data}")
        now_thailand = datetime.now(TIMEZONE_THAILAND)
        last_year_date = now_thailand - timedelta(days=365)
        historical_data = get_historical_data(last_year_date)
        historical_text = ""
        if historical_data:
            last_year_date_str = last_year_date.strftime("%d/%m/%Y")
            historical_text = f"\n\nเทียบกับปีที่แล้ว ({last_year_date_str})\nค่าน้ำอยู่ที่: {historical_data}"
        else:
            print("Historical data not found for last year.")
        formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M:%S")
        sponsor_line = "พื้นที่ผู้สนับสนุน..."
        message = (
            f"🌊 *แจ้งเตือนการปล่อยน้ำ เขื่อนเจ้าพระยา, ชัยนาท*\n"
            f"━━━━━━━━━━\n"
            f"✅ *ค่าปัจจุบัน:*\n{current_data}\n\n"
            f"⬅️ *ค่าเดิม (ก่อนหน้า):*\n{last_data if last_data else 'ไม่พบข้อมูลเดิม'}\n"
            f"━━━━━━━━━━\n"
            f"🗓️ {formatted_datetime}"
            f"{historical_text}\n\n"
            f"{sponsor_line}"
        )
        send_line_message(message)
        with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(current_data)
        append_to_historical_log(now_thailand, current_data)
        print("Appended new data to historical log and updated last_data.txt.")
    else:
        print("Could not retrieve current data. No notification sent.")

if __name__ == "__main__":
    main()
