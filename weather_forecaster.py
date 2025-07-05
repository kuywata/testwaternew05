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

# --- การตั้งค่าการแจ้งเตือน (แนะนำสำหรับ "ความแม่นยำสูงสุด") ---
# ตั้งค่าความน่าจะเป็นของฝนขั้นต่ำ (0.8 = 80%)
RAIN_CONFIDENCE_THRESHOLD = 0.8
# ปริมาณน้ำฝนขั้นต่ำที่คาดการณ์ (หน่วย: มิลลิเมตร) ถึงจะแจ้งเตือน
MIN_RAIN_VOLUME_MM = 1.0
# ต้องเจอฝนตกหนักติดต่อกันกี่ช่วงเวลา (2 ช่วง = ยืนยันแนวโน้ม 6 ชม. เต็ม)
CONSECUTIVE_PERIODS_NEEDED = 2
# จำนวนช่วงเวลาที่จะตรวจสอบล่วงหน้า (2 ช่วง = 6 ชั่วโมง)
FORECAST_PERIODS_TO_CHECK = 2


def get_weather_forecast():
    """
    ดึงข้อมูลพยากรณ์และตรวจสอบหาฝน/พายุที่เข้าเงื่อนไข "ยืนยันหลายชั้น"
    - ถ้าพบ: คืนค่าเป็นข้อความพยากรณ์
    - ถ้าไม่พบ: คืนค่าเป็น "NO_RAIN"
    - ถ้ามีข้อผิดพลาด: คืนค่าเป็น None
    """
    if not OPENWEATHER_API_KEY:
        print("OPENWEATHER_API_KEY is not set. Skipping.")
        return None

    # ขอข้อมูลให้ครอบคลุมจำนวนช่วงเวลาที่ต้องการตรวจสอบ
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={IN_BURI_LAT}&lon={IN_BURI_LON}&appid={OPENWEATHER_API_KEY}&units=metric&lang=th&cnt={FORECAST_PERIODS_TO_CHECK}"

    try:
        print(f"Fetching weather data for the next {FORECAST_PERIODS_TO_CHECK * 3} hours...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        forecast_data = response.json()

        confident_periods = []
        for forecast in forecast_data.get('list', []):
            weather_id = str(forecast.get('weather', [{}])[0].get('id', ''))
            pop = forecast.get('pop', 0)
            # ดึงปริมาณน้ำฝนใน 3 ชั่วโมงล่าสุด (ถ้ามี)
            rain_volume = forecast.get('rain', {}).get('3h', 0)

            # --- Logic การตรวจสอบแบบใหม่ (ยืนยันหลายชั้น) ---
            # 1. เป็นฝน (ID 5xx) หรือ พายุฝนฟ้าคะนอง (ID 2xx)
            is_rain_or_storm = weather_id.startswith('5') or weather_id.startswith('2')
            # 2. มีความน่าจะเป็นสูง
            is_confident_pop = pop >= RAIN_CONFIDENCE_THRESHOLD
            # 3. มีปริมาณน้ำฝนมากพอ
            is_significant_volume = rain_volume >= MIN_RAIN_VOLUME_MM

            print(f"Checking forecast at {datetime.fromtimestamp(forecast['dt'])}: ID {weather_id}, POP: {pop*100:.0f}%, Rain: {rain_volume}mm")

            if is_rain_or_storm and is_confident_pop and is_significant_volume:
                # ถ้าเข้าเงื่อนไขทั้งหมด ให้เก็บ forecast นี้ไว้
                confident_periods.append(forecast)
            else:
                # ถ้ามีช่วงไหนไม่เข้าเงื่อนไข ให้ล้างลิสต์แล้วเริ่มนับใหม่ (สำหรับความเข้มงวดสูงสุด)
                confident_periods = []

            # 4. ตรวจสอบว่าเจอติดต่อกันตามจำนวนที่กำหนดหรือยัง
            if len(confident_periods) >= CONSECUTIVE_PERIODS_NEEDED:
                print(f"SUCCESS: Found {len(confident_periods)} consecutive periods of heavy rain/storm.")

                # ใช้ข้อมูลของช่วงเวลาแรกที่เข้าเงื่อนไขในการสร้างข้อความ
                first_strong_forecast = confident_periods[0]
                weather = first_strong_forecast.get('weather', [{}])[0]
                
                # ดึงปริมาณฝนของช่วงเวลาแรกมาแสดงผล
                first_rain_volume = first_strong_forecast.get('rain', {}).get('3h', 0)

                tz_thailand = pytz.timezone('Asia/Bangkok')
                forecast_time_utc = datetime.fromtimestamp(first_strong_forecast['dt'])
                forecast_time_th = forecast_time_utc.astimezone(tz_thailand)

                # เพิ่ม Emoji ตามประเภทของสภาพอากาศ
                icon = "⛈️" if str(weather.get('id')).startswith('2') else "🌧️"

                message = (f"{icon} *พยากรณ์ฝนตกหนัก/พายุ (ยืนยันแล้ว)*\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"*พื้นที่: อ.อินทร์บุรี, สิงห์บุรี*\n\n"
                           f"▶️ *คาดการณ์:* {weather.get('description', 'N/A')}\n"
                           f"💧 *ปริมาณฝน:* ~{first_rain_volume:.1f} mm\n"
                           f"🗓️ *เวลาเริ่มประมาณ:* {forecast_time_th.strftime('%H:%M น.')} ({forecast_time_th.strftime('%d/%m')})")

                return message

        print(f"No consecutive heavy rain/storm detected meeting all criteria.")
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

    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M:%S")
    full_message = f"{message}\n\nอัปเดต: {formatted_datetime}"

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
            print("Forecast changed to 'NO_RAIN'. Not sending a notification, just updating status.")

        write_data(LAST_FORECAST_FILE, current_forecast)
    else:
        if current_forecast is None:
            print("Could not retrieve weather forecast. Skipping.")
        else:
            print("Forecast has not changed. No action needed.")

if __name__ == "__main__":
    main()
