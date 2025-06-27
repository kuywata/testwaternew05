import requests
import re
import json
from bs4 import BeautifulSoup
import os
from datetime import datetime
import pytz

URL = '[https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php](https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php)'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')

def get_water_data():
    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status()
        match = re.search(r'var json_data = (\[.*\]);', response.text)
        if not match:
            print("Could not find json_data variable in the page.")
            return None
        json_str = match.group(1)
        data = json.loads(json_str)
        station_data = data[0].get('itc_water', {}).get('C13', None)
        if station_data:
            storage = station_data.get('storage', '-')
            qmax = station_data.get('qmax', '-')
            return f"{storage}/ {qmax} cms"
        return None
    except (requests.exceptions.RequestException, json.JSONDecodeError, AttributeError) as e:
        print(f"An error occurred: {e}")
        return None

def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials are not set. Cannot send message.")
        return
    url = '[https://api.line.me/v2/bot/message/push](https://api.line.me/v2/bot/message/push)'
    headers = { 'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}' }
    payload = { 'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}] }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("LINE message sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending LINE message: {e.response.text if e.response else 'No response'}")

def main():
    last_data_file = 'last_data.txt'
    last_data = ''
    if os.path.exists(last_data_file):
        with open(last_data_file, 'r', encoding='utf-8') as f:
            last_data = f.read().strip()
    current_data = get_water_data()
    if current_data:
        print(f"Current data: {current_data}")
        print(f"Last saved data: {last_data}")
        if current_data != last_data:
            print("Data has changed! Sending notification...")
            
            # --- ส่วนของข้อความที่ปรับแต่งแล้ว ---
            tz_thailand = pytz.timezone('Asia/Bangkok')
            now_thailand = datetime.now(tz_thailand)
            formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M:%S")

            # ** แก้ไขชื่อผู้สนับสนุนตรงนี้ได้เลย **
            sponsor_name = "[airtest01]" 

            message = f"🌊 *แจ้งเตือนระดับน้ำเปลี่ยนแปลง!*\n" \
                      f"━━━━━━━━━━━━━━\n" \
                      f"*เขื่อนเจ้าพระยา, ชัยนาท*\n\n" \
                      f"✅ *ค่าปัจจุบัน*\n`{current_data}`\n\n" \
                      f"⬅️ *ค่าเดิม*\n`{last_data if last_data else 'N/A'}`\n" \
                      f"━━━━━━━━━━━━━━\n" \
                      f"🗓️ {formatted_datetime}\n\n" \
                      f"_Power by {ร้านจิปาถะ(ตลาดอินทร์บุรี)}_"
            # --- จบส่วนของข้อความ ---

            send_line_message(message)
            with open(last_data_file, 'w', encoding='utf-8') as f:
                f.write(current_data)
        else:
            print("Data has not changed.")
    else:
        print("Could not retrieve current data from JSON.")

if __name__ == "__main__":
    main()
