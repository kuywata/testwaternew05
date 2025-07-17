# weather_forecaster.py
import requests
import os
import time
from datetime import datetime
import pytz
import json # Import json for better state file management

# --- General settings ---
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.getenv('LINE_TARGET_ID')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# Coordinates for In Buri, Singburi
LATITUDE = 15.02
LONGITUDE = 100.34

# State file (using JSON for better structure)
STATE_FILE = 'weather_alert_state.json'

# --- Alert Thresholds (ปรับค่าตรงนี้เพื่อเปลี่ยนความไวของการแจ้งเตือน) ---
RAIN_CONF_THRESHOLD = 0.3    # โอกาสเกิดฝน ≥30%
MIN_RAIN_MM = 5.0           # ปริมาณน้ำฝนคาดการณ์ ≥5 มม. ใน 3 ชั่วโมง (Adjusted for potentially less strict alerts)
HEAT_THRESHOLD = 35.0        # อุณหภูมิคาดการณ์ ≥35 °C

# --- Lookahead & Cooldown Settings ---
LOOKAHEAD_PERIODS = 24       # จำนวนรายการพยากรณ์ที่จะดึงมา (3-hour intervals)
MAX_LEAD_HOURS = 12          # พิจารณาพยากรณ์ล่วงหน้าไม่เกิน 12 ชั่วโมง (Increased to catch events further out)
COOLDOWN_HOURS = 4           # รออย่างน้อย 4 ชั่วโมง ก่อนแจ้งเตือนเหตุการณ์ประเภทเดียวกันซ้ำ (Adjusted cooldown)


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
            if (forecast_time - now_utc).total_seconds() > MAX_LEAD_HOURS * 3600 or \
               (forecast_time - now_utc).total_seconds() < -1800: # Ignore past forecasts (with a 30 min buffer)
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

        print("No significant weather events found within the next 12 hours.")
        return 'NO_EVENT', None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching forecast: {e}")
        return None, None


def read_state(path):
    """Return content of state file as dict or default if missing/invalid."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Default state: no alerts sent, no cooldowns
        return {
            'last_alert_times': {}, # Stores last alert timestamp per event type (e.g., {'RAIN': 1678886400})
            'last_alerted_forecasts': {} # Stores {'event_type': {'dt': timestamp, 'value': float}}
        }


def write_state(path, state_data):
    with open(path, 'w') as f:
        json.dump(state_data, f, indent=4)


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
            f"⛈️ *แจ้งเตือน: ฝนตกหนัก*\n"
            f"พื้นที่: อ.อินทร์บุรี จ.สิงห์บุรี\n"
            f"คาดการณ์: {desc}, ปริมาณฝน ~{rain_mm:.1f} มม./3ชม.\n"
            f"เวลา: {dt_local_str}"
        )

    # HEAT
    tmax = forecast['main'].get('temp_max')
    return (
        f"🌡️ *แจ้งเตือน: อากาศร้อนจัด*\n"
        f"พื้นที่: อ.อินทร์บุรี จ.สิงห์บุรี\n"
        f"คาดการณ์: อุณหภูมิสูงสุด {tmax:.1f} °C\n"
        f"เวลา: {dt_local_str}"
    )


def send_line(msg):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials missing. Cannot send message.")
        return False

    timestamp = datetime.now(pytz.timezone('Asia/Bangkok')) \
                     .strftime('%d/%m/%Y %H:%M:%S')
    payload = {
        'to': LINE_TARGET_ID,
        'messages': [{'type': 'text', 'text': f"{msg}\n\n(อัปเดต: {timestamp})"}]
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
    state = read_state(STATE_FILE)
    last_alert_times = state.get('last_alert_times', {})
    last_alerted_forecasts = state.get('last_alerted_forecasts', {})

    event, forecast = get_weather_event()
    if event is None: # Error case
        return
    if event == 'NO_EVENT':
        # If no significant event is found, we should clear any 'last alerted forecast'
        # for events that are now in the past or no longer meet criteria.
        # This prevents old, irrelevant forecast data from blocking future alerts.
        # We don't clear cooldowns, as we want to prevent spam if the same event type reappears.
        print("No significant weather events found. State will not be updated for alerts.")
        return

    forecast_dt = forecast['dt'] # Unix timestamp of the forecast
    forecast_value = (forecast.get('rain', {}).get('3h', 0)
                      if event == 'RAIN'
                      else forecast['main'].get('temp_max'))

    now = time.time()
    
    # Check for cooldown for the specific event type
    if event in last_alert_times and now < last_alert_times[event] + COOLDOWN_HOURS * 3600:
        print(f"Event type '{event}' is in {COOLDOWN_HOURS}-hour cooldown. No alert needed.")
        return

    # Check if this exact forecast (time and value) was already alerted
    # This prevents re-alerting the exact same forecast if it's fetched again before cooldown.
    last_alerted_for_event = last_alerted_forecasts.get(event)
    if last_alerted_for_event:
        if last_alerted_for_event['dt'] == forecast_dt and \
           abs(last_alerted_for_event['value'] - forecast_value) < 0.1: # Small tolerance for float comparison
            print(f"Forecast for {event} at {datetime.utcfromtimestamp(forecast_dt).isoformat()}Z "
                  f"with value {forecast_value:.1f} was already alerted. No new alert needed.")
            return

    # If we reached here, it's either a new event type, a new forecast for an existing type,
    # or the cooldown has expired.
    print(f"New or updated event detected: {event} at {datetime.utcfromtimestamp(forecast_dt).isoformat()}Z. Preparing to send alert.")
    message = format_message(event, forecast)
    if send_line(message):
        state['last_alert_times'][event] = now
        state['last_alerted_forecasts'][event] = {
            'dt': forecast_dt,
            'value': forecast_value
        }
        write_state(STATE_FILE, state)
        print("Alert sent and state has been updated.")
    else:
        print("Alert failed to send. State will not be updated.")


if __name__ == "__main__":
    main()
