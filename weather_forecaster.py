# weather_forecaster.py (corrected)
import requests
import os
import time
import json
from datetime import datetime, timedelta
import pytz

# --- General settings ---
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID           = os.getenv('LINE_TARGET_ID')
OPENWEATHER_API_KEY      = os.getenv('OPENWEATHER_API_KEY')

# Coordinates for In Buri, Singburi
LATITUDE = 15.02
LONGITUDE = 100.34

# Thresholds
RAIN_CONF_THRESHOLD = 0.3    # Probability of precipitation ≥30%
MIN_RAIN_MM         = 5.0    # Rain volume ≥5 mm in 3h
HEAT_THRESHOLD      = 35.0   # Max temperature ≥35°C

FORECAST_HOURS = 12          # Look ahead this many hours
COOLDOWN_HOURS = 6           # Cooldown period for alerts (hours)
STATE_FILE     = 'state.json'


def read_state(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            'last_alert_times': {},
            'last_alerted_forecasts': {}
        }


def write_state(path, state):
    with open(path, 'w') as f:
        json.dump(state, f, indent=4)


def format_message(event, data):
    tz = pytz.timezone('Asia/Bangkok')
    timestamp = datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(tz).strftime('%Y-%m-%d %H:%M')
    if event == 'RAIN_NOW':
        return f"⛈️ [{timestamp}] ฝนกำลังตกตอนนี้"
    if event == 'FORECAST_RAIN':
        hour = datetime.fromtimestamp(data['dt'], tz=pytz.UTC).astimezone(tz).hour
        vol  = data['value']
        return f"🌧️ [{timestamp}] ฝนหนักคาดการณ์เวลา {hour}:00 (ปริมาณ {vol:.1f} มม.)"
    if event == 'HEAT_WAVE':
        hour = datetime.fromtimestamp(data['dt'], tz=pytz.UTC).astimezone(tz).hour
        tmp  = data['value']
        return f"🔥 [{timestamp}] อากาศร้อนจัดเวลา {hour}:00 (สูงสุด {tmp:.1f}°C)"
    return f"[{timestamp}] Unhandled event: {event}"


def send_line(msg):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("Error: LINE_TOKEN or TARGET_ID not set. Skipping LINE notify.")
        return False
    headers = {'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    payload = {'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': msg}]}
    try:
        r = requests.post('https://api.line.me/v2/bot/message/push', headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        print("Successfully sent message to LINE.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send LINE message: {e}")
        return False


def get_current_weather_event():
    if not OPENWEATHER_API_KEY:
        print("Error: OPENWEATHER_API_KEY not set. Skipping current weather check.")
        return None, None
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LATITUDE}&lon={LONGITUDE}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        resp = requests.get(url, timeout=10); resp.raise_for_status()
        data = resp.json()
        wid = str(data['weather'][0]['id'])
        if wid.startswith('5'):
            return 'RAIN_NOW', {'dt': int(time.time()), 'value': None}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching current weather: {e}")
    return None, None


def get_weather_event():
    if not OPENWEATHER_API_KEY:
        print("Error: OPENWEATHER_API_KEY not set. Skipping forecast check.")
        return None, None
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LATITUDE}&lon={LONGITUDE}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        resp = requests.get(url, timeout=10); resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching forecast: {e}")
        return None, None

    now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
    for entry in data.get('list', []):
        forecast_time = datetime.fromisoformat(entry['dt_txt']).replace(tzinfo=pytz.UTC)
        if forecast_time - now_utc > timedelta(hours=FORECAST_HOURS):
            break
        pop      = entry.get('pop', 0)
        rain_vol = entry.get('rain', {}).get('3h', 0)
        temp_max = entry.get('main', {}).get('temp_max', 0)
        epoch_dt = int(forecast_time.timestamp())
        wid_str  = str(entry['weather'][0]['id'])  # Convert int to str to check prefix
        if wid_str.startswith(('5', '2')) and pop >= RAIN_CONF_THRESHOLD and rain_vol >= MIN_RAIN_MM:
            return 'FORECAST_RAIN', {'dt': epoch_dt, 'value': rain_vol}
        if temp_max >= HEAT_THRESHOLD:
            return 'HEAT_WAVE', {'dt': epoch_dt, 'value': temp_max}
    return None, None


def main():
    state = read_state(STATE_FILE)
    last_alert_times        = state.get('last_alert_times', {})
    last_alerted_forecasts  = state.get('last_alerted_forecasts', {})

    # 1) Check current rain
    event_now, data_now = get_current_weather_event()
    if event_now == 'RAIN_NOW':
        now     = time.time()
        last_ts = last_alert_times.get(event_now, 0)
        if now - last_ts >= COOLDOWN_HOURS * 3600:
            if send_line(format_message(event_now, data_now)):
                state['last_alert_times'][event_now] = now
                write_state(STATE_FILE, state)
        return

    # 2) Check forecast events
    event_fc, data_fc = get_weather_event()
    if not event_fc:
        print("No significant weather events found within the next period.")
        return
    now        = time.time()
    last_ts    = last_alert_times.get(event_fc, 0)
    forecast_dt= data_fc['dt']
    forecast_val = data_fc['value']
    prev       = last_alerted_forecasts.get(event_fc, {})

    # Bypass cooldown if new forecast time
    bypass = forecast_dt > prev.get('dt', 0)
    if not bypass and now - last_ts < COOLDOWN_HOURS*3600:
        print("Within cooldown. Skipping alert.")
        return

    # Send forecast alert
    if send_line(format_message(event_fc, data_fc)):
        state['last_alert_times'][event_fc]       = now
        state['last_alerted_forecasts'][event_fc] = {'dt': forecast_dt, 'value': forecast_val}
        write_state(STATE_FILE, state)

if __name__ == '__main__':
    main()
