import requests
import json
import os
from datetime import datetime
import pytz

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
IN_BURI_LAT = 15.02
IN_BURI_LON = 100.34
# ชื่อไฟล์สำหรับบันทึกสถานะพยากรณ์ล่าสุด
LAST_FORECAST_FILE = 'last_forecast.txt'
# --- การตั้งค่าการแจ้งเตือน ---
# ตั้งค่าความน่าจะเป็นของฝนขั้นต่ำก่อนส่งแจ้งเตือน (0.7 = 70%)
RAIN_CONFIDENCE_THRESHOLD = 0.7 
# จำนวนช่วงเวลาที่จะตรวจสอบล่วงหน้า (1 ช่วง = 3 ชั่วโมง)
# 2 = 6 ชั่วโมง, 3 = 9 ชั่วโมง
FORECAST_PERIODS_TO_CHECK = 2

def get_weather_forecast():
    """
    ดึงข้อมูลพยากรณ์และตรวจสอบหาฝนที่มีความน่าจะเป็นสูง
    - ถ้าพบฝนที่เข้าเงื่อนไข: คืนค่าเป็นข้อความพยากรณ์ (สถานะ)
    - ถ้าไม่พบฝน หรือความน่าจะเป็นต่ำ: คืนค่าเป็น "NO_RAIN"
    - ถ้ามีข้อผิดพลาด: คืนค่าเป็น None
    """
    if not OPENWEATHER_API_KEY:
        print("OPENWEATHER_API_KEY is not set. Skipping weather check.")
        return None
    
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={IN_BURI_LAT}&lon={IN_BURI_LON}&appid={OPENWEATHER_API_KEY}&units=metric&lang=th&cnt={FORECAST_PERIODS_TO_CHECK}"
    
    try:
        print(f"Fetching weather data for the next {FORECAST_PERIODS_TO_CHECK * 3} hours...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        forecast_data = response.json()

        for forecast in forecast_data.get('list', []):
            weather = forecast.get('weather', [{}])[0]
            pop = forecast.get('pop', 0) # ความน่าจะเป็นของฝน (0-1)

            is_rain_event = str(weather.get('id', '')).startswith('5')
            is_confident = pop >= RAIN_CONFIDENCE_THRESHOLD

            print(f"Checking forecast at {datetime.fromtimestamp(forecast['dt'])}: Weather ID {weather.get('id')}, POP: {pop*100:.0f}%")

            if is_rain_event and is_confident:
                tz_thailand = pytz.timezone('Asia/Bangkok')
                forecast_time_utc = datetime.fromtimestamp(forecast['dt'])
                forecast_time_th = forecast_time_utc.astimezone(tz_thailand)
                
                # --- รูปแบบข้อความดั้งเดิม ---
                message = (f"🌧️ *พยากรณ์ฝนตก (ความมั่นใจ > {RAIN_CONFIDENCE_THRESHOLD*100:.0f}%)*\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"*พื้นที่: อ.อินทร์บุรี, สิงห์บุรี*\n\n"
                           f"▶️ *คาดการณ์:* {weather.get('description', 'N/A')}\n"
                           f"🗓️ *เวลาประมาณ:* {forecast_time_th.strftime('%H:%M น.')} ({forecast_time_th.strftime('%d/%m')})")
                
                print(f"Confident rain predicted! Details: {weather.get('description')} with {pop*100:.0f}% probability.")
                return message

        print(f"No rain predicted with >{RAIN_CONFIDENCE_THRESHOLD*100:.0f}% confidence in the next {FORECAST_PERIODS_TO_CHECK * 3} hours.")
        return "NO_RAIN"

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"An error occurred in get_weather_forecast: {e}")
        return None

def send_line_message(message):
    """ส่งข้อความไปยัง LINE"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials are not set. Cannot send message.")
        return
        
    tz_thailand = pytz.timezone('Asia/Bangkok')
    now_thailand = datetime.now(tz_thailand)
    
    # --- รูปแบบข้อความส่วนท้ายดั้งเดิม ---
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M:%S")
    full_message = f"{message}\nอัปเดต: {formatted_datetime}\n\nพื้นที่ผู้สนับสนุน"

    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    payload = {'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': full_message}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("LINE message sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending LINE message: {e.response.text if e.response else 'No response'}")

def read_last_data(file_path):
    """อ่านข้อมูลจากไฟล์"""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ''

def write_data(file_path, data):
    """เขียนข้อมูลลงไฟล์"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(data)

def main():
    """ตรรกะหลักของโปรแกรม"""
    last_forecast = read_last_data(LAST_FORECAST_FILE)
    current_forecast = get_weather_forecast()

    if current_forecast is not None and current_forecast != last_forecast:
        print(f"Forecast has changed from '{last_forecast}' to '{current_forecast}'.")
        
        if current_forecast != "NO_RAIN":
            print("Sending LINE notification for new high-confidence rain forecast...")
            send_line_message(current_forecast)
        else:
            print("Forecast changed to 'NO_RAIN' or low confidence. Not sending a notification, just updating status.")

        write_data(LAST_FORECAST_FILE, current_forecast)
    else:
        if current_forecast is None:
            print("Could not retrieve weather forecast. Skipping.")
        else:
            print("Forecast has not changed. No action needed.")

if __name__ == "__main__":
    main()
