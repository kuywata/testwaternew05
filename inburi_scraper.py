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
from selenium.webdriver.chrome.options import Options

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
            print(f"LINE API error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"LINE API request failed: {e}")

def get_inburi_data_selenium():
    print(f"[Attempt 1] Opening page (timeout=60s): {URL}")
    
    # Configure Chrome options for headless mode and CI/CD environment
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox") # Required for CI/CD environments
    chrome_options.add_argument("--disable-dev-shm-usage") # Recommended for CI/CD environments
    chrome_options.add_argument("--window-size=1920,1080") # Set window size for consistent rendering
    # Specify Google Chrome binary location
    chrome_options.binary_location = "/usr/bin/google-chrome" 

    driver = None
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            # Initialize the driver with the headless options
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            driver.get(URL)
            print(f"Attempt {attempt} opened page successfully.")

            # Wait for the specific station name (อินทร์บุรี) to be visible within the table.
            print(f"[Attempt {attempt}] Waiting for '{STATION_NAME_TO_FIND}' data (timeout=60s)...")
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located((By.XPATH, f"//div[@class='table-responsive']//table//*[contains(text(), '{STATION_NAME_TO_FIND}')]"))
            )
            
            # Find the target station data
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all rows in the table
            table_rows = soup.select("table tbody tr")
            
            data = None
            for row in table_rows:
                # Assuming the columns are consistent: Station Name (col 1), Water Level (col 4), Status (col 6), Diff to Bank (col 7)
                columns = row.find_all('td')
                if columns and len(columns) >= 7:
                    station_name = columns[1].text.strip()
                    if station_name == STATION_NAME_TO_FIND:
                        try:
                            # Extract relevant data
                            wl_str = columns[4].text.strip()
                            wl = float(wl_str) if wl_str else None
                            status = columns[6].text.strip()
                            diff_str = columns[7].text.strip()
                            diff_to_bank = float(diff_str) if diff_str else None
                            
                            # Find the update time (usually in a separate header or footer, checking common locations)
                            # This part might need adjustment if the website structure changes.
                            time_element = soup.find('p', class_='text-muted') # Example of a common time location
                            time_str = time_element.text.strip() if time_element else "N/A"
                            
                            # Clean time string to just the time and date
                            if "เวลา:" in time_str:
                                time_str = time_str.replace("ข้อมูล ณ เวลา:", "").strip()
                            
                            data = {
                                "station": station_name,
                                "water_level": wl,
                                "status": status,
                                "diff_to_bank": diff_to_bank,
                                "time": time_str
                            }
                            break
                        except ValueError as ve:
                            print(f"Error parsing data for {station_name}: {ve}")
                            data = None
            
            return data

        except TimeoutException:
            print(f"Attempt {attempt} timed out or data missing.")
            # Debugging: Print page source if timeout occurs to see what was loaded
            if driver:
                print("--- Page Source on Timeout ---")
                print(driver.page_source)
                print("------------------------------")
        except Exception as e:
            print(f"An error occurred during attempt {attempt}: {e}")
        finally:
            if driver:
                driver.quit()

    print(f"All {max_attempts} attempts failed to fetch data.")
    print("Could not retrieve new data in this run.")
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
                json.dump(current_data, f, ensure_ascii=False, indent=4)
        else:
            print("No new data, skipping notification.")
    else:
        print("Could not retrieve new data in this run.")
