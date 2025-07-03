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

def get_weather_forecast():
    if not OPENWEATHER_API_KEY:
        print("OPENWEATHER_API_KEY is not set. Skipping weather check.")
        return None
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={IN_BURI_LAT}&lon={IN_BURI_LON}&appid={OPENWEATHER_API_KEY}&units=metric&lang=th"
    try:
        print("Fetching weather data for In Buri...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        forecast_data = response.json()
        for forecast in forecast_data.get('list', [])[:2]:
            weather = forecast.get('weather', [{}])[0]
            if str(weather.get('id', '')).startswith('5'):
                tz_thailand = pytz.timezone('Asia/Bangkok')
                forecast_time_utc = datetime.fromtimestamp(forecast['dt'])
                forecast_time_th = forecast_time_utc.astimezone(tz_thailand)
                message = (f"🌧️ *พยากรณ์ฝนตก*\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"*พื้นที่: อ.อินทร์บุรี, สิงห์บุรี*\n\n"
                           f"▶️ *คาดการณ์:* {weather.get('description', 'N/A')}\n"
                           f"🗓️ *เวลาประมาณ:* {forecast_time_th.strftime('%H:%M น.')} ({forecast_time_th.strftime('%d/%m')})")
                print(f"Rain predicted: {message}")
                return message
        print("No rain predicted in the next 24 hours.")
        return "NO_RAIN"
    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"An error occurred in get_weather_forecast: {e}")
        return None

def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials are not set. Cannot send message.")
        return
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    payload = {'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}]}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("LINE message sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending LINE message: {e.response.text if e.response else 'No response'}")

def read_last_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ''

def write_data(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(data)

def main():
    last_rain_forecast = read_last_data('last_rain_forecast.txt')
    current_rain_forecast = get_weather_forecast()
    if current_rain_forecast and current_rain_forecast != last_rain_forecast:
        print("Rain forecast has changed! Sending notification...")
        if current_rain_forecast != "NO_RAIN":
            tz_thailand = pytz.timezone('Asia/Bangkok')
            now_thailand = datetime.now(tz_thailand)
            formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M:%S")
            full_message = f"{current_rain_forecast}\nอัปเดต: {formatted_datetime}\n\nพื้นที่ผู้สนับสนุน"
            send_line_message(full_message)
        write_data('last_rain_forecast.txt', current_rain_forecast)
    else:
        print("Rain forecast has not changed or could not be retrieved.")

if __name__ == "__main__":
    main()
