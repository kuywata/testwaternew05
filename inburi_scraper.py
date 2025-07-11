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
    ดึงข้อมูลน้ำจาก API และ fallback หลายชั้น
    """
    session = requests.Session()
    base_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    # 1. API via requests
    try:
        resp = session.get(BASE_URL, headers=base_headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        meta = soup.find('meta', {'name': 'csrf-token'})
        csrf_token = meta['content'] if meta else ''
        headers = {
            **base_headers,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': BASE_URL,
            'X-CSRF-TOKEN': csrf_token,
        }
        api_resp = session.get(FULL_API_URL, headers=headers, timeout=30)
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
        print(f"API (requests) failed: {e}")

    # 2. Selenium fetch JSON via browser
    try:
        print("Fallback: Selenium fetching JSON...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(BASE_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        script = (
            "const callback = arguments[0];"
            f"fetch('{API_URL}', {{credentials:'same-origin'}})"
            ".then(r=>r.json()).then(json=>callback(json))"
            ".catch(e=>callback({{'error':e.toString()}}));"
        )
        data = driver.execute_async_script(script)
        driver.quit()
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

    # 3. BeautifulSoup table parse
    try:
        print("Fallback: parsing HTML table via BeautifulSoup...")
        resp = session.get(BASE_URL, headers=base_headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table')
        if table:
            headers = [th.text.strip() for th in table.find('thead').find_all('th')]
            idx_id = next(i for i,h in enumerate(headers) if 'สถานี' in h)
            idx_am = next(i for i,h in enumerate(headers) if 'อำเภอ' in h)
            idx_tb = next(i for i,h in enumerate(headers) if 'ตำบล' in h)
            idx_lvl = next(i for i,h in enumerate(headers) if 'ระดับน้ำ' in h)
            idx_bank = next(i for i,h in enumerate(headers) if 'ตลิ่ง' in h)
            for tr in table.find('tbody').find_all('tr'):
                cols = [td.text.strip() for td in tr.find_all('td')]
                if cols[idx_id] == str(STATION_ID_TO_FIND):
                    lvl = float(cols[idx_lvl])
                    bank = float(cols[idx_bank])
                    return {
                        'station': f"ต.{cols[idx_tb]} อ.{cols[idx_am]}",
                        'water_level': lvl,
                        'bank_level': bank,
                        'overflow': lvl - bank
                    }
    except Exception as e:
        print(f"BeautifulSoup table parse failed: {e}")

    # 4. Selenium HTML scrape fallback
    try:
        print("Final fallback: Selenium HTML scraping...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(BASE_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'table tbody tr')))
        rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
        for r in rows:
            cells = r.find_elements(By.TAG_NAME, 'td')
            if cells and cells[0].text.strip() == str(STATION_ID_TO_FIND):
                return {
                    'station': f"ต.{cells[3].text.strip()} อ.{cells[2].text.strip()}",
                    'water_level': float(cells[-3].text.strip()),
                    'bank_level': float(cells[-2].text.strip()),
                    'overflow': float(cells[-3].text.strip()) - float(cells[-2].text.strip())
                }
        driver.quit()
    except Exception as e:
        print(f"Selenium HTML scraping failed: {e}")

    print("All methods failed: station not found.")
    return None


def main():
    data = get_inburi_river_data()
    if data:
        with open('last_inburi_data.txt', 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False))


if __name__ == '__main__':
    main()
