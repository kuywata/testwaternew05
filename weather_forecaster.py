# weather_forecaster.py
import requests
import os
import time
from datetime import datetime
import pytz

# --- General settings ---
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.getenv('LINE_TARGET_ID')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# Coordinates for In Buri, Singburi
LATITUDE = 15.02
LONGITUDE = 100.34

# State files
LAST_FORECAST_ID_FILE = 'last_forecast_id.txt'
LAST_ALERT_TIME_FILE = 'last_alert_time.txt'

# --- Alert Thresholds (ปรับค่าตรงนี้เพื่อเปลี่ยนความไวของการแจ้งเตือน) ---
RAIN_CONF_THRESHOLD = 0.3    # โอกาสเกิดฝน ≥30%
MIN_RAIN_MM = 10.0           # ปริมาณน้ำฝนคาดการณ์ ≥10 มม. ใน 3 ชั่วโมง
HEAT_THRESHOLD = 35.0        # อุณหภูมิคาดการณ์ ≥35 °C

# --- Lookahead & Cooldown Settings ---
LOOKAHEAD_PERIODS = 24       # จำนวนรายการพยากรณ์ที่จะดึงมา (3-hour intervals)
MAX_LEAD_HOURS = 6           # พิจารณาพยากรณ์ล่วงหน้าไม่เกิน 6 ชั่วโมง
COOLDOWN_HOURS = 6           # รออย่างน้อย 6 ชั่วโมง ก่อนแจ้งเตือนเหตุการณ์ประเภทเดียวกันซ้ำ


def get_weather_event():
    """Fetch forecast and return ('RAIN' or 'HEAT', forecast_dict),
       or ('NO_EVENT', None), or (None, None) on error."""
    if not OPENWEATHER_API_KEY:
        print("Error: OPENWEATHER_API_KEY is not set. Skipping.")
        return None, None

    now_utc = datetime.utcnow()
    url = (
        f'https://api.openweathermap.org/data/2.5/forecast'
        f'?lat={LATITUDE}&lon={LONGITUDE}'
        f'&appid={OPENWEATHER_API_KEY}&units=metric'
        f'&cnt={LOOKAHEAD_PERIODS}&lang=th'
    )

    try:
        print(f"Fetching weather data from OpenWeatherMap...")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json().get('list', [])

        for entry in data:
            forecast_time = datetime.utcfromtimestamp(entry['dt'])
            
            # พิจารณาเฉพาะพยากรณ์ในช่วง MAX_LEAD_HOURS เท่านั้น
            if (forecast_time - now_utc).total_seconds() > MAX_LEAD_HOURS * 3600:
                continue

            # ตรวจสอบเงื่อนไขฝนตกหนัก
            pop = entry.get('pop', 0)
            rain_vol = entry.get('rain', {}).get('3h', 0)
            # Weather ID for rain starts with '5' (Rain) or '2' (Thunderstorm)
            weather_id = str(entry.get('weather', [{}])[0].get('id', ''))

            if (weather_id.startswith('5') or weather_id.startswith('2')) \
               and pop >= RAIN_CONF_THRESHOLD and rain_vol >= MIN_RAIN_MM:
                print(f"Found potential RAIN event at {forecast_time.isoformat()}Z")
                return 'RAIN', entry

            # ตรวจสอบเงื่อนไขอากาศร้อนจัด
            tmax = entry.get('main', {}).get('temp_max')
            if tmax is not None and tmax >= HEAT_THRESHOLD:
                print(f"Found potential HEAT event at {forecast_time.isoformat()}Z")
                return 'HEAT', entry

        print("No significant weather events found within the next 6 hours.")
        return 'NO_EVENT', None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching forecast: {e}")
        return None, None


def read_file(path):
    """Return content or empty string if missing."""
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ''


def write_file(path, content):
    with open(path, 'w') as f:
        f.write(str(content))


def format_message(event, forecast):
    tz = pytz.timezone('Asia/Bangkok')
    dt_local_str = datetime.utcfromtimestamp(forecast['dt']) \
                           .replace(tzinfo=pytz.UTC) \
                           .astimezone(tz) \
                           .strftime('%H:%M น. วันที่ %d/%m/%Y')

    if event == 'RAIN':
        desc = forecast['weather'][0].get('description', 'N/A')
        rain_mm = forecast.get('rain', {}).get('3h', 0)
        return (
            f"⛈️ *แจ้งเตือนฝนตกหนัก*\n"
            f"พื้นที่: อ.อินทร์บุรี จ.สิงห์บุรี\n"
            f"ลักษณะอากาศ: {desc}\n"
            f"ปริมาณฝนคาดการณ์: ~{rain_mm:.1f} มม./3ชม.\n"
            f"ช่วงเวลา: {dt_local_str}"
        )

    # HEAT
    tmax = forecast['main'].get('temp_max')
    return (
        f"🌡️ *แจ้งเตือนอากาศร้อนจัด*\n"
        f"พื้นที่: อ.อินทร์บุรี จ.สิงห์บุรี\n"
        f"อุณหภูมิสูงสุดคาดการณ์: {tmax:.1f} °C\n"
        f"ช่วงเวลา: {dt_local_str}"
    )


def send_line(msg):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials missing. Cannot send message.")
        return False

    timestamp = datetime.now(pytz.timezone('Asia/Bangkok')) \
                     .strftime('%d/%m/%Y %H:%M:%S')
    payload = {
        'to': LINE_TARGET_ID,
        'messages': [{'type': 'text', 'text': f"{msg}\n\n(อัปเดตเมื่อ: {timestamp})"}]
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    try:
        print("Sending message to LINE...")
        r = requests.post('https://api.line.me/v2/bot/message/push',
                          headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        print("Successfully sent message to LINE.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send LINE message: {e}")
        return False


def main():
    last_id = read_file(LAST_FORECAST_ID_FILE)
    last_alert_time = float(read_file(LAST_ALERT_TIME_FILE) or 0)

    event, forecast = get_weather_event()
    if event is None or event == 'NO_EVENT':
        return

    # สร้าง ID ของเหตุการณ์ปัจจุบันที่ไม่ซ้ำกัน
    value = (forecast.get('rain', {}).get('3h', 0)
             if event == 'RAIN'
             else forecast['main'].get('temp_max'))
    current_id = f"{event}:{forecast['dt']}:{value:.1f}"
    now = time.time()

    prev_event_type = last_id.split(':')[0] if ':' in last_id else None

    if current_id == last_id:
        print(f"Event '{current_id}' is unchanged. No alert needed.")
        return

    # ตรวจสอบ Cooldown เฉพาะเมื่อประเภทเหตุการณ์เหมือนกับครั้งล่าสุด
    if event == prev_event_type and now < last_alert_time + COOLDOWN_HOURS * 3600:
        print(f"Event type '{event}' is in {COOLDOWN_HOURS}-hour cooldown. No alert needed.")
        return
        
    print(f"New event detected: {current_id}. Preparing to send alert.")
    message = format_message(event, forecast)
    if send_line(message):
        write_file(LAST_ALERT_TIME_FILE, now)
        write_file(LAST_FORECAST_ID_FILE, current_id)
        print("Alert sent and state has been updated.")
    else:
        print("Alert failed to send. State will not be updated.")


if __name__ == "__main__":
    main()
