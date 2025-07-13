import json
import os
import time
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --- Constants ---
URL = "https://singburi.thaiwater.net/wl"
STATION_NAME_TO_FIND = "อินทร์บุรี"
LAST_DATA_FILE = 'last_inburi_data.txt'

# --- LINE credentials from environment ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')

def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials are not set. Cannot send message.")
        return
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {
        'to': LINE_TARGET_ID,
        'messages': [{'type': 'text', 'text': message}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"LINE API error: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Error sending LINE message: {e}")


def get_inburi_data_selenium(retries: int = 3):
    """
    Fetch water level data for the target station with Selenium.
    Retries up to `retries` times with longer timeouts and implicit waits.
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )

    for attempt in range(1, retries + 1):
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        # Increase page load and lookup timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        try:
            print(f"[Attempt {attempt}] Opening page (timeout=60s): {URL}")
            driver.get(URL)

            print(f"[Attempt {attempt}] Waiting for data table (timeout=30s)...")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//table[.//th[contains(text(), 'สถานี')]]"))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find(
                'table',
                lambda t: t.find('th', string=lambda txt: txt and 'สถานี' in txt)
            )
            if not table:
                print("Data table not found; retrying...")
                raise TimeoutException()

            # Parse rows looking for our station
            for row in table.find('tbody').find_all('tr'):
                cells = row.find_all('td')
                if len(cells) > 5 and STATION_NAME_TO_FIND in cells[1].get_text(strip=True):
                    time_str = cells[2].get_text(strip=True)
                    wl_text = cells[3].get_text(strip=True).replace(',', '')
                    status_text = cells[4].get_text(strip=True)
                    diff_text = cells[5].get_text(strip=True).replace(',', '')

                    wl = float(wl_text)
                    diff = float(diff_text)
                    print(f"Found station '{STATION_NAME_TO_FIND}': time={time_str}, wl={wl}, status={status_text}, diff={diff}")
                    return {
                        'time': time_str,
                        'water_level': wl,
                        'status': status_text,
                        'diff_to_bank': diff
                    }

            print(f"Station '{STATION_NAME_TO_FIND}' not found in table; retrying...")
            raise TimeoutException()

        except TimeoutException:
            print(f"Attempt {attempt} timed out or data missing.")
        except Exception as e:
            print(f"Attempt {attempt} error: {e}")
        finally:
            driver.quit()
            time.sleep(5)

    print(f"All {retries} attempts failed to fetch data.")
    return None


if __name__ == '__main__':
    last_data = {}
    if os.path.exists(LAST_DATA_FILE):
        with open(LAST_DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                last_data = json.load(f)
            except json.JSONDecodeError:
                last_data = {}

    current_data = get_inburi_data_selenium()

    if current_data:
        # Compare timestamp or water level
        if (
            not last_data or
            last_data.get('time') != current_data.get('time') or
            last_data.get('water_level') != current_data.get('water_level')
        ):
            print("Data changed, sending notification...")
            wl = current_data['water_level']
            status = current_data['status']
            diff = current_data['diff_to_bank']
            time_str = current_data['time']

            message = (
                f"🌊 อัปเดตระดับน้ำอินทร์บุรี ({time_str})\n"
                f"━━━━━━━━━━━━━━\n"
                f"▶️ ระดับน้ำ: *{wl:.2f} ม.*\n"
                f"▶️ สถานะ: *{status}*\n"
                f"▶️ ต่ำกว่าตลิ่ง: {diff:.2f} ม."
            )

            send_line_message(message)
            with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            print("Saved new data.")
        else:
            print("No change in data; no notification sent.")
    else:
        print("Could not retrieve new data in this run.")
