import requests
import json
import urllib.parse
from bs4 import BeautifulSoup

# Constants
BASE_URL = "https://singburi.thaiwater.net/wl"
# เพิ่ม slash ท้าย API URL เพื่อให้แน่ใจว่าเรียก endpoint ถูกต้อง
API_URL = "https://singburi.thaiwater.net/api/v1/tele_waterlevel/"
STATION_ID_TO_FIND = 3724  # รหัสสถานีที่ต้องการค้นหา


def get_inburi_river_data():
    """
    ดึงข้อมูลโดยการเรียก API ของเว็บโดยตรง โดยใช้ Header และ CSRF token ที่ถูกต้อง
    """
    print("Attempting direct API call with comprehensive headers...")
    try:
        session = requests.Session()

        # 1. สร้าง Header พื้นฐานเพื่อเลียนแบบเบราว์เซอร์
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        # 2. เข้าหน้าเว็บหลักเพื่อรับ Session, Cookies และ CSRF meta tag
        print(f"Visiting {BASE_URL} to get session cookies and CSRF token...")
        main_page_response = session.get(BASE_URL, headers=base_headers, timeout=30)
        main_page_response.raise_for_status()

        # 3. พยายามอ่าน CSRF token จาก meta tag ใน HTML
        soup = BeautifulSoup(main_page_response.text, 'html.parser')
        meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
        if meta_tag and meta_tag.get('content'):
            csrf_token = meta_tag['content']
            print("Successfully retrieved CSRF token from HTML meta tag.")
        else:
            # fallback: อ่าน XSRF-TOKEN cookie
            xsrf_cookie = (
                session.cookies.get('XSRF-TOKEN')
                or session.cookies.get('X-XSRF-TOKEN')
            )
            if not xsrf_cookie:
                print("Fatal Error: Could not find CSRF token (meta or cookie). The site may have changed.")
                return None
            csrf_token = urllib.parse.unquote(xsrf_cookie)
            print("Successfully retrieved CSRF token from cookie.")

        # 4. สร้าง Header สำหรับเรียก API
        api_headers = {
            **base_headers,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': BASE_URL,
            'X-CSRF-TOKEN': csrf_token,
        }

        print(f"Calling API at {API_URL}...")
        api_response = session.get(API_URL, headers=api_headers, timeout=30)

        if api_response.status_code != 200:
            print(f"Unexpected status code: {api_response.status_code}")
            print(f"Response text (first 500 chars): {api_response.text[:500]}")
            return None

        # 5. แปลงข้อมูล JSON (จับ error อย่างชัดเจน)
        try:
            all_stations_data = api_response.json()
        except json.JSONDecodeError as e:
            print("JSON Decode Error: Failed to parse API response:", e)
            print(f"Response text (first 500 chars): {api_response.text[:500]}")
            return None

        # 6. หา Station ที่ต้องการ
        target = next((s for s in all_stations_data if s.get('id') == STATION_ID_TO_FIND), None)
        if not target:
            print(f"Could not find station {STATION_ID_TO_FIND} in the API response.")
            return None

        station_name = f"ต.{target.get('tumbon')} อ.{target.get('amphoe')}"
        water_level = float(target.get('level', 0))
        bank_level = float(target.get('bank', 0))
        overflow = water_level - bank_level

        print(f"✅ Data for station: {station_name} (ID: {STATION_ID_TO_FIND})")
        print(f"  - Water Level: {water_level:.2f} m, Bank Level: {bank_level:.2f} m.")
        return {
            "station": station_name,
            "water_level": water_level,
            "bank_level": bank_level,
            "overflow": overflow
        }

    except requests.exceptions.RequestException as e:
        print(f"An HTTP error occurred: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print(f"Response Body: {e.response.text[:500]}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def main():
    data = get_inburi_river_data()
    if data:
        # บันทึกข้อมูลลงไฟล์
        with open("last_inburi_data.txt", "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
