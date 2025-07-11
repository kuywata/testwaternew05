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

# Constants
BASE_URL = "https://singburi.thaiwater.net/wl"
API_URL = "/api/v1/tele_waterlevel"
FULL_API_URL = "https://singburi.thaiwater.net" + API_URL
STATION_ID_TO_FIND = 3724  # รหัสสถานีที่ต้องการค้นหา


def get_inburi_river_data():
    """
    พยายามเรียก API ก่อน หากล้มเหลวจะใช้ Selenium ในการ fetch JSON ในบริบทเบราว์เซอร์
    และถ้ายังไม่ได้ผล จึงสกรัปปิ้ง HTML ตาราง
    """
    print("Attempting API call via requests...")
    session = requests.Session()
    base_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        # ดึง CSRF token
        resp = session.get(BASE_URL, headers=base_headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        meta = soup.find('meta', {'name': 'csrf-token'})
        if meta and meta.get('content'):
            csrf_token = meta['content']
        else:
            xsrf = session.cookies.get('XSRF-TOKEN') or session.cookies.get('X-XSRF-TOKEN')
            csrf_token = urllib.parse.unquote(xsrf) if xsrf else ''

        headers = {
            **base_headers,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': BASE_URL,
            'X-CSRF-TOKEN': csrf_token,
        }
        api_resp = session.get(FULL_API_URL + API_URL, headers=headers, timeout=30)
        api_resp.raise_for_status()
        data = api_resp.json()
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
    except Exception as e:
        print(f"Requests API call failed: {e}")

    # Fallback 1: Selenium fetch JSON inside browser
    print("Falling back: using Selenium to fetch JSON via browser...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(BASE_URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        script = f"""
            var callback = arguments[0];
            fetch('{API_URL}', {{ credentials: 'same-origin' }})
              .then(r => r.json())
              .then(json => callback(json))
              .catch(err => callback({{'error': err.toString()}}));
        """
        data = driver.execute_async_script(script)
        if isinstance(data, list):
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
    except Exception as e:
        print(f"Selenium JSON fetch failed: {e}")
    finally:
        driver.quit()

    # Fallback 2: Selenium HTML table scraping
    print("Final fallback: scraping HTML table...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(BASE_URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'table tbody tr'))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, 'td')
            if any(cell.text.strip() == str(STATION_ID_TO_FIND) for cell in cells):
                tumbon = cells[3].text.strip()
                amphoe = cells[2].text.strip()
                level = float(cells[-3].text.strip())
                bank = float(cells[-2].text.strip())
                return {
                    'station': f"ต.{tumbon} อ.{amphoe}",
                    'water_level': level,
                    'bank_level': bank,
                    'overflow': level - bank
                }
        print(f"Station {STATION_ID_TO_FIND} not found in table.")
        return None
    finally:
        driver.quit()


def main():
    data = get_inburi_river_data()
    if data:
        with open('last_inburi_data.txt', 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False))


if __name__ == '__main__':
    main()
