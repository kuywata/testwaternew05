import requests
import json
import os
import time
from datetime import datetime
import pytz

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
IN_BURI_LAT = 15.02
IN_BURI_LON = 100.34
LAST_FORECAST_ID_FILE = 'last_forecast_id.txt'
LAST_ALERT_TIME_FILE = 'last_alert_time.txt'

# --- 🎯 การตั้งค่าการแจ้งเตือน ---
RAIN_CONFIDENCE_THRESHOLD = 0.3    # ความน่าจะเป็นฝน ≥ 30%
MIN_RAIN_VOLUME_MM = 10.0          # ฝน ≥ 10 มม.
HEAT_TEMP_THRESHOLD = 35.0         # อุณหภูมิสูงสุด ≥ 35°C
FORECAST_PERIODS_TO_CHECK = 24     # ตรวจสอบล่วงหน้า 24 ชั่วโมง
MAX_LEAD_TIME_HOURS = 6            # พยากรณ์ภายใน 6 ชม.
ALERT_COOLDOWN_HOURS = 6           # เว้นแจ้งเตือนอย่างน้อย 6 ชม.

def get_weather_events():
    """
    ตรวจสอบทั้งฝนหนักและอากาศร้อนจัด
    คืนค่า tuple (event_type, forecast) หรือ ("NO_EVENT", None) หรือ (None, None) เมื่อเกิดข้อผิดพลาด
    """
    if not OPENWEATHER_API_KEY:
        print("OPENWEATHER_API_KEY is not set. Skipping.")
        return None, None

    now_unix = int(time.time())
    url = (
        f"https://api.openweathermap.org/data/2.5/forecast?lat={IN_BURI_LAT}&lon={IN_BURI_LON}"
        f"&appid={OPENWEATHER_API_KEY}&units=metric&lang=th&cnt={FORECAST_PERIODS_TO_CHECK}"
    )

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        forecast_list = response.json().get('list', [])

        for f in forecast_list:
            # ข้ามช่วงที่อยู่นอก lead time
            if f['dt'] > now_unix + MAX_LEAD_TIME_HOURS * 3600:
                continue

            # ตรวจฝนหนัก
            wid = str(f.get('weather', [{}])[0].get('id', ''))
            pop = f.get('pop', 0)
            rain = f.get('rain', {}).get('3h', 0)
            if (wid.startswith('5') or wid.startswith('2')) and pop >= RAIN_CONFIDENCE_THRESHOLD and rain >= MIN_RAIN_VOLUME_MM:
                return 'RAIN', f

            # ตรวจอากาศร้อนจัด
            temp_max = f.get('main', {}).get('temp_max')
            if temp_max is not None and temp_max >= HEAT_TEMP_THRESHOLD:
                return 'HEAT', f

        return 'NO_EVENT', None
    except Exception as e:
        print(f"Error in get_weather_events: {e}")
        return None, None

def format_message(event_type, forecast):
    tz = pytz.timezone('Asia/Bangkok')
    dt_bk = datetime.utcfromtimestamp(forecast['dt']).replace(tzinfo=pytz.UTC).astimezone(tz)

    if event_type == 'RAIN':
        w = forecast.get('weather', [{}])[0]
        rain = forecast.get('rain', {}).get('3h', 0)
        icon = '⛈️'
        message = (
            f"{icon} *แจ้งเตือนฝนตกหนัก*\n"
            f"*พื้นที่:* อ.อินทร์บุรี, สิงห์บุรี\n"
            f"*สภาพ:* {w.get('description','N/A')}\n"
            f"*ฝน:* ~{rain:.1f} mm\n"
            f"*เวลา:* {dt_bk.strftime('%H:%M %d/%m/%Y')}"
        )
    else:
        temp = forecast.get('main', {}).get('temp_max')
        icon = '🌡️'
        message = (
            f"{icon} *แจ้งเตือนอากาศร้อนจัด*\n"
            f"*พื้นที่:* อ.อินทร์บุรี, สิงห์บุรี\n"
            f"*อุณหภูมิสูงสุด:* {temp:.1f} °C\n"
            f"*เวลา:* {dt_bk.strftime('%H:%M %d/%m/%Y')}"
        )
    return message

def send_line_message(msg):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials missing")
        return False
    ts = datetime.now(pytz.timezone('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M:%S')
    payload = {'to': LINE_TARGET_ID, 'messages': [{'type':'text', 'text':f"{msg}\nอัปเดต: {ts}"}]}
    try:
        r = requests.post(
            'https://api.line.me/v2/bot/message/push',
            headers={'Content-Type':'application/json', 'Authorization':f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'},
            json=payload, timeout=10
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending LINE: {e}")
        return False

def read_file(path):
    return open(path, 'r').read().strip() if os.path.exists(path) else ''

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

def main():
    last_id = read_file(LAST_FORECAST_ID_FILE)
    last_alert_time = float(read_file(LAST_ALERT_TIME_FILE) or 0)

    event_type, forecast = get_weather_events()
    if event_type == 'NO_EVENT':
        print("No rain or heat events detected. No notification sent.")
        return
    if event_type is None:
        return

    # สร้างรหัสสถานะใหม่
    value = forecast.get('rain', {}).get('3h', 0) if event_type == 'RAIN' else forecast.get('main', {}).get('temp_max')
    current_id = f"{event_type}:{forecast['dt']}:{value}"
    now = time.time()

    last_event = last_id.split(':')[0] if last_id else None
    if current_id != last_id:
        if now >= last_alert_time + ALERT_COOLDOWN_HOURS * 3600 or event_type != last_event:
            msg = format_message(event_type, forecast)
            if send_line_message(msg):
                write_file(LAST_ALERT_TIME_FILE, str(now))
                write_file(LAST_FORECAST_ID_FILE, current_id)
        else:
            print("Within cooldown period. No new notification.")
    else:
        print("Event unchanged. No notification.")

if __name__ == '__main__':
    main()
