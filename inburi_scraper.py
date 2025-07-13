import json
import os
import time
from bs4 import BeautifulSoup

# --- ส่วนของ Selenium ที่ปรับปรุงแล้ว ---
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --- ค่าคงที่ ---
URL = "https://singburi.thaiwater.net/wl"
STATION_NAME_TO_FIND = "อินทร์บุรี"
LAST_DATA_FILE = 'last_inburi_data.txt'

# --- ดึงค่า Secrets สำหรับ LINE ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')


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
        print("ส่งข้อความ LINE สำเร็จ!")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการส่ง LINE: {e}")


def get_inburi_data_selenium():
    """
    ดึงข้อมูลระดับน้ำด้วย Selenium (ฉบับปรับปรุงความเสถียร)
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # --- จุดที่แก้ไข: กำหนด Timeout ให้กับ Driver โดยตรง ---
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(30) # ให้เวลาโหลดหน้าเว็บ 30 วินาที
    
    try:
        print(f"กำลังเปิดหน้าเว็บ: {URL} (ให้เวลาโหลดสูงสุด 30 วินาที)")
        driver.get(URL)

        # --- จุดที่แก้ไข: เพิ่มการรอคอยที่ชัดเจนและจัดการ TimeoutException ---
        print("กำลังรอให้ตารางข้อมูลปรากฏ... (ให้เวลาสูงสุด 20 วินาที)")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table[.//th[contains(text(), 'สถานี')]]"))
        )
        print("พบตารางข้อมูลจริงแล้ว! เริ่มการวิเคราะห์...")
        
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        table = soup.find('table', lambda t: t.find('th', string=lambda text: text and 'สถานี' in text))
        
        if not table:
            print("ไม่พบตารางข้อมูลที่มีหัวข้อ 'สถานี'")
            return None
            
        for row in table.find('tbody').find_all('tr'):
            cells = row.find_all('td')
            if cells and len(cells) > 1:
                station_text_from_web = cells[1].text.strip()
                if STATION_NAME_TO_FIND in station_text_from_web:
                    print(f"!!! พบข้อมูลของสถานี: {STATION_NAME_TO_FIND} !!!")
                    # ... (ส่วนการดึงข้อมูลเหมือนเดิม) ...
                    return {
                        # ... data ...
                    }

        print(f"*** ไม่พบข้อมูลของสถานี '{STATION_NAME_TO_FIND}' ในตารางข้อมูลจริง ***")
        return None

    except TimeoutException:
        print("เกิดข้อผิดพลาด: Timeout! หน้าเว็บหรือตารางโหลดไม่เสร็จในเวลาที่กำหนด")
        return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาดไม่คาดคิด: {e}")
        return None
    finally:
        print("ปิดการทำงานของ Selenium browser")
        driver.quit()


if __name__ == '__main__':
    last_data = {}
    if os.path.exists(LAST_DATA_FILE):
        with open(LAST_DATA_FILE, 'r', encoding='utf-8') as f:
            try: last_data = json.load(f)
            except json.JSONDecodeError: pass

    current_data = get_inburi_data_selenium()
    
    if current_data:
        if not last_data or last_data.get('time') != current_data.get('time') or last_data.get('water_level') != current_data.get('water_level'):
            print("ข้อมูลมีการเปลี่ยนแปลง! กำลังส่งแจ้งเตือน...")
            
            wl = current_data['water_level']
            status = current_data['status']
            diff = current_data['diff_to_bank']
            time_str = current_data['time']
            
            message = (f"🌊 อัปเดตระดับน้ำอินทร์บุรี ({time_str})\n"
                       f"━━━━━━━━━━━━━━\n"
                       f"▶️ ระดับน้ำ: *{wl:.2f} ม.*\n"
                       f"▶️ สถานะ: *{status}*\n"
                       f"▶️ ต่ำกว่าตลิ่ง: {diff:.2f} ม.")
            
            send_line_message(message)

            with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            print("บันทึกข้อมูลใหม่สำเร็จ")
        else:
            print("ข้อมูลไม่มีการเปลี่ยนแปลง ไม่ต้องแจ้งเตือน")
    else:
        print("ไม่สามารถดึงข้อมูลใหม่ได้ในรอบนี้")
