import requests
import re
import json
import os
from datetime import datetime, timedelta
import pytz
import time

# --- ค่าคงที่และ URL ---
URL = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')
HISTORICAL_LOG_FILE = 'historical_log.csv'
LAST_DATA_FILE = 'last_data.txt' # เพิ่มตัวแปรสำหรับชื่อไฟล์ last_data.txt

# --- ฟังก์ชันดึงข้อมูล ---
def get_water_data():
    """ดึงข้อมูลระดับน้ำล่าสุด"""
    try:
        timestamp = int(time.time())
        url_with_cache_bust = f"{URL}?_={timestamp}"
        response = requests.get(url_with_cache_bust, timeout=15)
        response.raise_for_status()
        match = re.search(r'var json_data = (\[.*\]);', response.text)
        if not match: return None
        data = json.loads(match.group(1))
        station_data = data[0].get('itc_water', {}).get('C13', None)
        if station_data:
            # ดึงเฉพาะ 'qmax' ซึ่งเป็นค่าปล่อยน้ำ (ถ้ามี)
            # ถ้าต้องการ 'storage' ด้วย ก็ใช้ f"{station_data.get('storage', '-')}/ {station_data.get('qmax', '-')} cms"
            # แต่โจทย์ระบุ "การปล่อยน้ำ" จึงเน้นที่ qmax
            return f"{station_data.get('qmax', '-')} cms" # เปลี่ยนให้ส่งค่า qmax เท่านั้น
        return None
    except Exception as e:
        print(f"Error in get_water_data: {e}")
        return None

# --- ฟังก์ชันสำหรับข้อมูลย้อนหลัง (ฉบับแก้ไข) ---
def get_historical_data(target_date):
    """ค้นหาข้อมูลที่ใกล้เคียงกับวันเวลาของปีที่แล้วจากไฟล์ log"""
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
                
                # --- ส่วนที่แก้ไข ---
                # ตรวจสอบว่า log_date ที่อ่านมามี timezone หรือไม่
                # .tzinfo is None คือไม่มี timezone (naive)
                if log_date.tzinfo is None:
                    # ถ้าไม่มี ให้กำหนด timezone ของไทยให้มัน
                    log_date = TIMEZONE_THAILAND.localize(log_date)
                # --- จบส่วนแก้ไข ---
                
                # ตอนนี้ log_date เป็น aware และสามารถเปรียบเทียบได้แล้ว
                if start_range <= log_date <= end_range:
                    diff = abs(target_date - log_date)
                    if diff < smallest_diff:
                        smallest_diff = diff
                        closest_entry = value
            except ValueError:
                continue
                
    return closest_entry

def append_to_historical_log(now, data):
    """บันทึกข้อมูลปัจจุบันลงในไฟล์ log"""
    with open(HISTORICAL_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{now.isoformat()},{data}\n")

# --- ฟังก์ชันส่ง LINE ---
def send_line_message(message):
    """ส่งข้อความไปยัง LINE"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials not set.")
        return
    url = 'https://api.line.me/v2/bot/message/push'
    headers = { 'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}' }
    payload = { 'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}] }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("LINE message sent successfully!")
    except Exception as e:
        print(f"Error sending LINE message: {e}")

# --- การทำงานหลัก ---
def main():
    # อ่านค่า last_data ก่อนดึงข้อมูลปัจจุบัน
    last_data = ''
    if os.path.exists(LAST_DATA_FILE): # ใช้ LAST_DATA_FILE ที่เพิ่งกำหนด
        with open(LAST_DATA_FILE, 'r', encoding='utf-8') as f:
            last_data = f.read().strip()
            
    current_data = get_water_data()
    
    # ตรวจสอบว่าดึงข้อมูลปัจจุบันมาได้หรือไม่
    if current_data:
        print(f"Current data retrieved: {current_data}")
        
        now_thailand = datetime.now(TIMEZONE_THAILAND)
        
        last_year_date = now_thailand - timedelta(days=365)
        historical_data = get_historical_data(last_year_date)
        
        historical_text = ""
        if historical_data:
            last_year_date_str = last_year_date.strftime("%d/%m/%Y")
            # บรรทัดใหม่ (เอา ` ออก)
            historical_text = f"\n\nเทียบกับปีที่แล้ว ({last_year_date_str})\nค่าน้ำอยู่ที่: {historical_data}"
        else:
            print("Historical data not found for last year.")
        
        formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M:%S")
        
        sponsor_line = "พื้นที่ผู้สนับสนุน..."
        
        # ปรับเปลี่ยนข้อความ LINE ให้ชัดเจนว่าเป็นการแจ้งเตือน "การปล่อยน้ำ"
        # และรวมค่า last_data เข้าไป
       message = (f"🌊 *แจ้งเตือนการปล่อยน้ำ เขื่อนเจ้าพระยา, ชัยนาท*\n"
           f"━━━━━━━━━━\n"
           f"✅ *ค่าปัจจุบัน*\n`{current_data}`\n\n"
           f"⬅️ *ค่าเดิม (ก่อนหน้า)*\n`{last_data if last_data else 'ไม่พบข้อมูลเดิม'}`\n"
           f"━━━━━━━━━━\n"
           f"🗓️ {formatted_datetime}"
           f"{historical_text}\n\n"
           f"{sponsor_line}")

        send_line_message(message)
        
        # บันทึกข้อมูลปัจจุบันลงใน last_data.txt ทุกครั้งที่ส่งแจ้งเตือน
        with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(current_data)
        
        # บันทึกข้อมูลลงใน historical_log.csv ทุกครั้งที่ส่งแจ้งเตือน
        append_to_historical_log(now_thailand, current_data)
        print("Appended new data to historical log and updated last_data.txt.")
        
    else:
        print("Could not retrieve current data. No notification sent.")

if __name__ == "__main__":
    main()
