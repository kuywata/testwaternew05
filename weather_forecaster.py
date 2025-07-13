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

# Alert thresholds
RAIN_CONF_THRESHOLD = 0.3    # ≥30% chance
MIN_RAIN_MM = 10.0           # ≥10 mm in 3 h
HEAT_THRESHOLD = 35.0        # ≥35 °C
LOOKAHEAD_PERIODS = 24       # forecast entries to fetch
MAX_LEAD_HOURS = 6           # only consider next 6 h
COOLDOWN_HOURS = 6           # wait at least 6 h between same-event alerts


def get_weather_event():
    """Fetch forecast and return ('RAIN' or 'HEAT', forecast_dict),
       or ('NO_EVENT', None), or (None, None) on error."""
    if not OPENWEATHER_API_KEY:
        print("OPENWEATHER_API_KEY missing, skipping.")
        return None, None

    now = int(time.time())
    url = (
        f'https://api.openweathermap.org/data/2.5/forecast'
        f'?lat={LATITUDE}&lon={LONGITUDE}'
        f'&appid={OPENWEATHER_API_KEY}&units=metric'
        f'&cnt={LOOKAHEAD_PERIODS}&lang=th'
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json().get('list', [])

        for entry in data:
            dt = entry['dt']
            if dt > now + MAX_LEAD_HOURS * 3600:
                continue

            # Heavy rain?
            pop = entry.get('pop', 0)
            rain_vol = entry.get('rain', {}).get('3h', 0)
            wid = str(entry.get('weather', [{}])[0].get('id', ''))
            if (wid.startswith('5') or wid.startswith('2')) \
               and pop >= RAIN_CONF_THRESHOLD and rain_vol >= MIN_RAIN_MM:
                return 'RAIN', entry

            # Heat wave?
            tmax = entry.get('main', {}).get('temp_max')
            if tmax is not None and tmax >= HEAT_THRESHOLD:
                return 'HEAT', entry

        return 'NO_EVENT', None

    except Exception as e:
        print(f"Error fetching forecast: {e}")
        return None, None


def read_file(path):
    """Return content or empty string if missing."""
    return open(path).read().strip() if os.path.exists(path) else ''


def write_file(path, content):
    with open(path, 'w') as f:
        f.write(str(content))


def format_message(event, forecast):
    tz = pytz.timezone('Asia/Bangkok')
    dt_local = datetime.utcfromtimestamp(forecast['dt']) \
                   .replace(tzinfo=pytz.UTC) \
                   .astimezone(tz) \
                   .strftime('%H:%M %d/%m/%Y')

    if event == 'RAIN':
        desc = forecast['weather'][0].get('description', 'N/A')
        rain_mm = forecast.get('rain', {}).get('3h', 0)
        return (
            f"⛈️ *แจ้งเตือนฝนตกหนัก*\n"
            f"*พื้นที่:* อ.อินทร์บุรี, จ.สิงห์บุรี\n"
            f"*สภาพ:* {desc}\n"
            f"*ปริมาณฝน:* ~{rain_mm:.1f} มม.\n"
            f"*เวลา:* {dt_local}"
        )

    # HEAT
    tmax = forecast['main'].get('temp_max')
    return (
        f"🌡️ *แจ้งเตือนอากาศร้อนจัด*\n"
        f"*พื้นที่:* อ.อินทร์บุรี, จ.สิงห์บุรี\n"
        f"*อุณหภูมิสูงสุด:* {tmax:.1f} °C\n"
        f"*เวลา:* {dt_local}"
    )


def send_line(msg):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials missing.")
        return False

    timestamp = datetime.now(pytz.timezone('Asia/Bangkok')) \
                     .strftime('%d/%m/%Y %H:%M:%S')
    payload = {
        'to': LINE_TARGET_ID,
        'messages': [{'type': 'text', 'text': f"{msg}\n\nอัปเดต: {timestamp}"}]
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    try:
        r = requests.post('https://api.line.me/v2/bot/message/push',
                          headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"LINE send error: {e}")
        return False


def main():
    last_id = read_file(LAST_FORECAST_ID_FILE)
    last_alert = float(read_file(LAST_ALERT_TIME_FILE) or 0)

    event, forecast = get_weather_event()
    if event == 'NO_EVENT':
        print("No relevant weather event.")
        return
    if event is None:
        return

    # Build a new unique ID
    value = (forecast.get('rain', {}).get('3h', 0)
             if event == 'RAIN'
             else forecast['main'].get('temp_max'))
    curr_id = f"{event}:{forecast['dt']}:{value}"
    now = time.time()

    prev_event = last_id.split(':')[0] if last_id else None

    if curr_id != last_id:
        if now >= last_alert + COOLDOWN_HOURS * 3600 or event != prev_event:
            msg = format_message(event, forecast)
            if send_line(msg):
                write_file(LAST_ALERT_TIME_FILE, now)
                write_file(LAST_FORECAST_ID_FILE, curr_id)
                print("Alert sent and state updated.")
            else:
                print("Failed to send alert.")
        else:
            print("In cooldown; no alert.")
    else:
        print("Event unchanged; no alert.")


if __name__ == "__main__":
    main()
