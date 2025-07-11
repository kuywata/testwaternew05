import requests
import json
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Constants
BASE_URL = "https://singburi.thaiwater.net/wl"
API_URL = "https://singburi.thaiwater.net/api/v1/tele_waterlevel"
STATION_ID_TO_FIND = 3724  # รหัสสถานีที่ต้องการค้นหา


def get_inburi_river_data():
    """
    พยายามเรียก API ก่อน หากล้มเหลวจะใช้ Selenium สกรัปปิ้งหน้าเว็บโดยตรง
    """
    print("Attempting direct API call with comprehensive headers...")
    session = requests.Session()
    base_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        # GET หน้าเว็บหลัก เพื่อรับ Cookies และ CSRF token
        main_resp = session.get(BASE_URL, headers=base_headers, timeout=30)
        main_resp.raise_for_status()
        # อ่าน CSRF จาก meta tag
        soup = BeautifulSoup(main_resp.text, 'html.parser')
        meta = soup.find('meta', {'name': 'csrf-token'})
        if meta and meta.get('content'):
            csrf_token = meta['content']
            print("CSRF token from meta tag.")
        else:
            # fallback cookie
            xsrf = session.cookies.get('XSRF-TOKEN') or session.cookies.get('X-XSRF-TOKEN')
            if not xsrf:
                raise ValueError("Cannot find CSRF token.")
            csrf_token = urllib.parse.unquote(xsrf)
            print("CSRF token from cookie.")

        api_headers = {
            **base_headers,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': BASE_URL,
            'X-CSRF-TOKEN': csrf_token,
        }
        api_resp = session.get(API_URL, headers=api_headers, timeout=30)
        if api_resp.status_code == 200:
            try:
                data = api_resp.json()
                # ค้นหา station
                for s in data:
                    if s.get('id') == STATION_ID_TO_FIND:
                        lvl = float(s.get('level', 0))
                        bank = float(s.get('bank', 0))
                        return {
                            'station': f"ต.{s.get('tumbon')} อ.{s.get('amphoe')}",
                            'water_level': lvl,
                            'bank_level': bank,
                            'overflow': lvl - bank
                        }
            except json.JSONDecodeError:
                pass
    except Exception as e:
        print(f"API call failed: {e}")

    # Fallback: Selenium scraping
    print("Falling back to Selenium scraping...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(BASE_URL)
        # รอให้ตารางโหลด
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'table tbody tr'))
        )
        # ค้นหา row โดยใช้รหัสสถานี
        row = None
        rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, 'td')
            if cells and cells[0].text.strip() == str(STATION_ID_TO_FIND):
                row = cells
                break
        if not row:
            print(f"Station {STATION_ID_TO_FIND} not found via Selenium.")
            return None
        # สมมติ columns: 0=id,1=province,2=amphoe,3=tumbon,4=level,5=bank
        tumbon = row[3].text
        amphoe = row[2].text
        lvl = float(row[4].text)
        bank = float(row[5].text)
        return {
            'station': f"ต.{tumbon} อ.{amphoe}",
            'water_level': lvl,
            'bank_level': bank,
            'overflow': lvl - bank
        }
    finally:
        driver.quit()


def main():
    data = get_inburi_river_data()
    if data:
        with open('last_inburi_data.txt', 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False))


if __name__ == '__main__':
    main()
