import requests
import os
import json
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# --- การตั้งค่าทั่วไป ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')

# --- การตั้งค่าสำหรับสคริปต์นี้โดยเฉพาะ ---
BASE_URL = "https://singburi.thaiwater.net/wl"
API_URL = "https://singburi.thaiwater.net/api/v1/tele_waterlevel"
LAST_DATA_FILE = 'last_inburi_data.txt'
STATION_ID_TO_FIND = "C.35"
NOTIFICATION_THRESHOLD_METERS = 0.20

def get_inburi_river_data():
    """
    ดึงข้อมูลโดยการเรียก API ของเว็บโดยตรง
    เพิ่มขั้นตอนการดีบักเพื่อตรวจสอบการตอบกลับของ API
    """
    print("Fetching data via direct API call...")
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }
        
        print(f"Visiting {BASE_URL} to get CSRF token...")
        main_page_response = session.get(BASE_URL, headers=headers, timeout=20)
        main_page_response.raise_for_status()
        
        soup = BeautifulSoup(main_page_response.text, 'html.parser')
        token_tag = soup.find('meta', {'name': 'csrf-token'})
        
        if not token_tag or not token_tag.get('content'):
            print("Error: Could not find CSRF token on the main page.")
            return None
            
        csrf_token = token_tag.get('content')
        print(f"Successfully retrieved CSRF token.")

        api_headers = headers.copy()
        api_headers.update({
            'X-CSRF-TOKEN': csrf_token,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': BASE_URL
        })
        
        print(f"Calling API at {API_URL}...")
        api_response = session.get(API_URL, headers=api_headers, timeout=20)
        
        # --- ส่วนที่เพิ่มเข้ามาเพื่อดีบัก ---
        print(f"API response status code: {api_response.status_code}")
        # ตรวจสอบว่า Response มีเนื้อหาหรือไม่
        if not api_response.text.strip():
            print("Error: API returned an empty response body.")
            return None
        
        print(f"API response text (first 500 chars): {api_response.text[:500]}")
        # ------------------------------------

        # เช็ค Status code อีกครั้งก่อนแปลง JSON
        api_response.raise_for_status()

        # แปลงข้อมูล JSON และค้นหาสถานี
        all_stations_data = api_response.json()
        target_station_data = next((s for s in all_stations_data if s.get('id') == STATION_ID_TO_FIND), None)

        if not target_station_data:
            print(f"Could not find station {STATION_ID_TO_FIND} in the API response.")
            return None
        
        station_name = f"ต.{target_station_data.get('tumbon')} อ.{target_station_data.get('amphoe')}"
        water_level = float(target_station_data.get('level', 0))
        bank_level = float(target_station_data.get('bank', 0))
        overflow = water_level - bank_level
        
        print(f"Successfully found data for station: {station_name} (ID: {STATION_ID_TO_FIND})")
        print(f"  - Water Level: {water_level:.2f} m, Bank Level: {bank_level:.2f} m.")

        return {"station": station_name, "water_level": water_level, "bank_level": bank_level, "overflow": overflow}

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: Failed to parse API response. The error was: {e}")
        # ไม่ต้องพิมพ์ response text อีก เพราะพิมพ์ไปแล้วข้างบน
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# ฟังก์ชันที่เหลือทั้งหมด (send_line_message, read_last_data, write_data, main) ให้ใช้ของเดิม ไม่ต้องแก้ไข
def send_line_message(data, change_amount):
    now_thailand = datetime.now(TIMEZONE_THAILAND)
    formatted_datetime = now_thailand.strftime("%d/%m/%Y %H:%M น.")
    
    last_level = read_last_data(LAST_DATA_FILE)

    if last_level is None:
        change_text = "รายงานข้อมูลครั้งแรก"
    elif change_amount == 0.0:
        change_text = "ระดับน้ำไม่เปลี่ยนแปลง"
    else:
        change_direction_icon = "⬆️" if change_amount > 0 else "⬇️"
        change_text = f"เปลี่ยนแปลง {change_direction_icon} {abs(change_amount):.2f} ม."
    
    if data['overflow'] > 0:
        status_text, status_icon, overflow_text = "⚠️ *น้ำล้นตลิ่ง*", "🚨", f"{data['overflow']:.2f} ม."
    else:
        status_text, status_icon, overflow_text = "✅ *ระดับน้ำปกติ*", "🌊", f"ต่ำกว่าตลิ่ง {-data['overflow']:.2f} ม."

    message = (
