import requests
from bs4 import BeautifulSoup
import json
import time
import os # เพิ่ม os สำหรับอ่านค่า secrets

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- ค่าคงที่ ---
URL = "https://singburi.thaiwater.net/wl"
STATION_NAME_TO_FIND = "อินทร์บุรี"
LAST_DATA_FILE = 'last_inburi_data.txt'

# --- ดึงค่า Secrets สำหรับ LINE ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')


def send_line_message(message):
    """
    ฟังก์ชันสำหรับส่งข้อความไปที่ LINE
    """
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials are not set. Cannot send message.")
        return
    
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    payload = {'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("ส่งข้อความ LINE สำเร็จ!")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการส่ง LINE: {e}")


def get_inburi_data_selenium():
    # ... (ส่วนของฟังก์ชัน get_inburi_data_selenium เหมือนเดิมทุกประการ ไม่ต้องแก้ไข) ...
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        print(f"กำลังเปิดหน้าเว็บด้วย Selenium: {URL}")
        driver.get(URL)

        print("กำลังรอให้ JavaScript โหลดตารางข้อมูล...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
        print("พบตารางบนหน้าเว็บแล้ว! เริ่มการวิเคราะห์...")
        
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        table = None
        all_tables = soup.find_all('table')
        print(f"พบตารางทั้งหมด {len(all_tables)} ตารางบนหน้าเว็บ")
        for t in all_tables:
            if t.find('th', string=lambda text: text and 'สถานี' in text):
                table = t
                print("พบตารางข้อมูลจริงแล้ว!")
                break

        if not table:
            print("ไม่พบตารางข้อมูลที่มีหัวข้อ 'สถานี'")
            return None
            
        for row in table.find('tbody').find_all('tr'):
            cells = row.find_all('td')
            if cells and len(cells) > 1:
                station_text_from_web = cells[1].text.strip()
                if STATION_NAME_TO_FIND in station_text_from_web:
                    print(f"!!! พบข้อมูลของสถานี: {STATION_NAME_TO_FIND} !!!")
                    
                    water_level_text = cells[2].text.strip()
                    bank_level_text = cells[3].text.strip()
                    diff_text = cells[5].text.strip().replace('ต่ำกว่าตลิ่ง (ม.)','').strip()

                    data = {
                        "station_name": station_text_from_web.replace('\n', ' '),
                        "water_level": float(water_level_text) if water_level_text != '-' else 0.0,
                        "bank_level": float(bank_level_text) if bank_level_text != '-' else 0.0,
                        "status": cells[4].text.strip(),
                        "diff_to_bank": float(diff_text) if diff_text != '-' else 0.0,
                        "time": cells[6].text.strip(),
                        "source": URL
                    }
                    return data

        print(f"*** ไม่พบข้อมูลของสถานี '{STATION_NAME_TO_FIND}' ในตารางข้อมูลจริง ***")
        return None

    except Exception as e:
        print(f"เกิดข้อผิดพลาดระหว่างการทำงานของ Selenium: {e}")
        return None
    finally:
        print("ปิดการทำงานของ Selenium browser")
        driver.quit()


if __name__ == '__main__':
    # --- ส่วนที่แก้ไข: เพิ่ม Logic การเปรียบเทียบและแจ้งเตือน ---
    
    # 1. อ่านข้อมูลเก่า (ถ้ามี)
    last_data = {}
    if os.path.exists(LAST_DATA_FILE):
        with open(LAST_DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                last_data = json.load(f)
            except json.JSONDecodeError:
                print("ไฟล์ข้อมูลเก่ามีปัญหา ไม่สามารถอ่านได้")

    # 2. ดึงข้อมูลใหม่
    current_data = get_inburi_data_selenium()
    
    if current_data:
        # 3. เปรียบเทียบข้อมูล (เช็คจากเวลาและระดับน้ำ)
        if not last_data or last_data.get('time') != current_data.get('time') or last_data.get('water_level') != current_data.get('water_level'):
            print("ข้อมูลมีการเปลี่ยนแปลง! กำลังส่งแจ้งเตือน...")

            # 4. จัดรูปแบบข้อความและส่ง LINE
            wl = current_data['water_level']
            status = current_data['status']
            diff = current_data['diff_to_bank']
            time = current_data['time']
            
            message = (f"🌊 อัปเดตระดับน้ำอินทร์บุรี ({time})\n"
                       f"━━━━━━━━━━━━━━\n"
                       f"▶️ ระดับน้ำ: *{wl:.2f} ม.*\n"
                       f"▶️ สถานะ: *{status}*\n"
                       f"▶️ ต่ำกว่าตลิ่ง: {diff:.2f} ม.")
            
            send_line_message(message)

            # 5. บันทึกข้อมูลใหม่ทับของเก่า
            with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            print("บันทึกข้อมูลใหม่สำเร็จ")

        else:
            print("ข้อมูลไม่มีการเปลี่ยนแปลง ไม่ต้องแจ้งเตือน")
    else:
        print("ไม่สามารถดึงข้อมูลใหม่ได้")
