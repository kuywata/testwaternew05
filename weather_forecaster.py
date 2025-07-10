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
LAST_FORECAST_ID_FILE = 'last_forecast_id.txt'

# --- 🎯 การตั้งค่าการแจ้งเตือน (ปรับให้เข้มงวดขึ้นเพื่อเน้นฝนหนัก/พายุ) ---
RAIN_CONFIDENCE_THRESHOLD = 0.75       # เดิม 0.6: โอกาสเกิดฝนต้องสูงถึง 75%
MIN_RAIN_VOLUME_MM = 3.0             # เดิม 0.5: ปริมาณน้ำฝนใน 3 ชม. ต้องมากกว่า 3.0 มม. (ถือว่าหนัก)
CONSECUTIVE_PERIODS_NEEDED = 2       # เดิม 1:   ต้องเจอเงื่อนไขฝนหนักต่อเนื่อง 2 ช่วง (รวม 6 ชม.) เพื่อยืนยันว่าเป็นพายุจริง
FORECAST_PERIODS_TO_CHECK = 4        # ตรวจสอบ 12 ชั่วโมงข้างหน้า (4*3 ชม.)


def get_weather_forecast():
    """
    ดึงข้อมูลพยากรณ์และตรวจสอบหาฝน/พายุที่เข้าเงื่อนไข
    - ถ้าพบ: คืนค่าเป็น object ของ forecast แรกที่เข้าเงื่อนไข
    - ถ้าไม่พบ: คืนค่าเป็น "NO_RAIN"
    - ถ้ามีข้อผิดพลาด: คืนค่าเป็น None
    """
    if not OPENWEATHER_API_KEY:
        print("OPENWEATHER_API_KEY is not set. Skipping.")
        return None

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
            rain_volume = forecast.get('rain', {}).get('3h', 0)

            is_rain_or_storm = weather_id.startswith('5') or weather_id.startswith('2')
            is_confident_pop = pop >= RAIN_CONFIDENCE_THRESHOLD
            is_significant_volume = rain_volume >= MIN_RAIN_VOLUME_MM

            print(f"Checking forecast at {datetime.fromtimestamp(forecast['dt'])}: ID {weather_id}, POP: {pop*100:.0f}%, Rain: {rain_volume}mm")

            if is_rain_or_storm and is_confident_pop and is_significant_volume:
                confident_periods.append(forecast)
            else:
                confident_periods = []

            if len(confident_periods) >= CONSECUTIVE_PERIODS_NEEDED:
                print(f"SUCCESS: Found {len(confident_periods)} consecutive periods of heavy rain/storm meeting criteria.")
                return confident_periods[0]

        print(f"No heavy rain/storm detected meeting the strict criteria.")
        return "NO_RAIN"

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"An error occurred in get_weather_forecast: {e}")
        return None

def format_forecast_message(forecast_object):
    """จัดรูปแบบข้อความ LINE จาก object พยากรณ์"""
    weather = forecast_object.get('weather', [{}])[0]
    rain_volume = forecast_object.get('rain', {}).get('3h', 0)
    
    tz_thailand = pytz.timezone('Asia/Bangkok')
    forecast_time_utc = datetime.fromtimestamp(forecast_object['dt'])
    forecast_time_th = forecast_time_utc.astimezone(tz_thailand)

    icon = "⛈️" if str(weather.get('id')).startswith('2') else "🌧️"

    # 🎯 ปรับข้อความให้ชัดเจนว่าเป็นการเตือนภัย "ฝนตกหนัก"
    message = (f"{icon} *แจ้งเตือนพายุ/ฝนตกหนัก*\n"
               f"━━━━━━━━━━━━━━\n"
               f"*พื้นที่: อ.อินทร์บุรี, สิงห์บุรี*\n\n"
               f"▶️ *ลักษณะอากาศ:* {weather.get('description', 'N/A')}\n"
               f"💧 *ปริมาณฝนคาดการณ์:* ~{rain_volume:.1f} mm\n"
               f"🗓️ *เวลาที่คาดว่าจะเริ่ม:* {forecast_time_th.strftime('%H:%M น.')} ({forecast_time_th.strftime('%d/%m')})")
    return message

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
    last_notified_id = read_last_data(LAST_FORECAST_ID_FILE)
    current_forecast_object = get_weather_forecast()

    if current_forecast_object is None:
        print("Could not retrieve weather forecast. Skipping.")
        return

    current_status_id = ""
    if isinstance(current_forecast_object, dict):
        current_status_id = str(current_forecast_object.get('dt', ''))
    else:
        current_status_id = current_forecast_object

    if current_status_id != last_notified_id:
        print(f"Forecast ID has changed from '{last_notified_id}' to '{current_status_id}'.")

        if isinstance(current_forecast_object, dict):
            print("New heavy rain event detected. Formatting and sending LINE notification...")
            message_to_send = format_forecast_message(current_forecast_object)
            send_line_message(message_to_send)
        else:
            print("Forecast changed to 'NO_RAIN'. No notification needed, just updating status.")
        
        write_data(LAST_FORECAST_ID_FILE, current_status_id)
    else:
        print("Forecast status has not changed. No action needed.")


if __name__ == "__main__":
    main()
