import requests
from bs4 import BeautifulSoup
import json
import time

# --- เพิ่ม Library ของ Selenium ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- ค่าคงที่ ---
URL = "https://singburi.thaiwater.net/wl"
STATION_NAME_TO_FIND = "อินทร์บุรี"

def get_inburi_data_selenium():
    """
    ดึงข้อมูลระดับน้ำด้วย Selenium เพื่อให้รอ JavaScript โหลดข้อมูลเสร็จก่อน
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')  # รันแบบไม่แสดงหน้าจอ
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # ใช้ try...finally เพื่อให้แน่ใจว่า browser จะถูกปิดเสมอ
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        print(f"กำลังเปิดหน้าเว็บด้วย Selenium: {URL}")
        driver.get(URL)

        # --- จุดสำคัญ: รอจนกว่าข้อมูลในตารางจะปรากฏ ---
        # เรารอแถวแรก (tr) ใน tbody ของตาราง โดยให้เวลารอสูงสุด 20 วินาที
        print("กำลังรอให้ JavaScript โหลดตารางข้อมูล...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )
        print("ตารางข้อมูลปรากฏขึ้นแล้ว! เริ่มดึงข้อมูล...")
        
        # เมื่อข้อมูลมาครบแล้ว ให้ดึง HTML ทั้งหมดของหน้าที่แสดงผลอยู่
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        table = soup.find('table')
        if not table:
            print("ไม่พบตารางข้อมูล แม้จะใช้ Selenium แล้ว")
            return None
            
        for row in table.find('tbody').find_all('tr'):
            cells = row.find_all('td')
            if cells and STATION_NAME_TO_FIND in cells[1].text:
                print(f"พบข้อมูลของสถานี: {STATION_NAME_TO_FIND}")
                
                water_level_text = cells[2].text.strip()
                bank_level_text = cells[3].text.strip()
                diff_text = cells[5].text.strip().replace('ต่ำกว่าตลิ่ง (ม.)','').strip()

                data = {
                    "station_name": cells[1].text.strip().replace('\n', ' '),
                    "water_level": float(water_level_text) if water_level_text != '-' else 0.0,
                    "bank_level": float(bank_level_text) if bank_level_text != '-' else 0.0,
                    "status": cells[4].text.strip(),
                    "diff_to_bank": float(diff_text) if diff_text != '-' else 0.0,
                    "time": cells[6].text.strip(),
                    "source": URL
                }
                return data

        print(f"ไม่พบข้อมูลของสถานี '{STATION_NAME_TO_FIND}' ในตาราง")
        return None

    except Exception as e:
        print(f"เกิดข้อผิดพลาดระหว่างการทำงานของ Selenium: {e}")
        return None
    finally:
        print("ปิดการทำงานของ Selenium browser")
        driver.quit()


if __name__ == '__main__':
    # เปลี่ยนมาเรียกใช้ฟังก์ชันของ Selenium
    river_data = get_inburi_data_selenium() 
    
    if river_data:
        print("\nข้อมูลที่ดึงได้:")
        print(json.dumps(river_data, indent=2, ensure_ascii=False))
        
        with open('last_inburi_data.txt', 'w', encoding='utf-8') as f:
            json.dump(river_data, f, ensure_ascii=False, indent=2)
        print("\nบันทึกข้อมูลลง last_inburi_data.txt สำเร็จ")
    else:
        print("ไม่สามารถดึงข้อมูลได้")
