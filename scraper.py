# ใส่โค้ดนี้แทนที่ฟังก์ชัน get_water_data เดิมในไฟล์ scraper.py

import requests
from bs4 import BeautifulSoup
import re

# ... (ส่วนค่าคงที่อื่นๆ ด้านบนคงไว้เหมือนเดิม) ...

def get_water_data(timeout=30):
    """
    ดึงข้อมูลปริมาณน้ำโดยการค้นหาจากข้อความอ้างอิงที่ตายตัว ("ที่ท้ายเขื่อนเจ้าพระยา")
    แล้วจึงค้นหาข้อมูลจากโครงสร้าง HTML ที่อยู่ถัดไป ทำให้มีความแม่นยำและเสถียรสูง
    """
    try:
        # ใช้ requests เพื่อดึงหน้า HTML มาโดยตรง
        response = requests.get(URL, timeout=timeout)
        response.raise_for_status()  # ตรวจสอบว่าดึงข้อมูลสำเร็จ
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. หา tag ที่มีข้อความ "ที่ท้ายเขื่อนเจ้าพระยา" เพื่อใช้เป็นจุดอ้างอิง
        anchor_tag = soup.find('strong', string='ที่ท้ายเขื่อนเจ้าพระยา')

        if not anchor_tag:
            print("Error: ไม่พบจุดอ้างอิง 'ที่ท้ายเขื่อนเจ้าพระยา' ในหน้าเว็บ")
            return None

        # 2. ข้อมูลที่ต้องการอยู่ในแถว (tr) ถัดไป
        data_row = anchor_tag.find_parent('tr').find_next_sibling('tr')

        if not data_row:
            print("Error: ไม่พบแถวของข้อมูลที่อยู่ถัดจากจุดอ้างอิง")
            return None

        # 3. ในแถวนั้น ให้หาช่อง (td) ที่มีข้อมูลปริมาณน้ำ
        data_cell = data_row.find('td', class_='text_bold')

        if not data_cell:
            print("Error: ไม่พบช่องของข้อมูล (td.text_bold)")
            return None

        # 4. ดึงข้อความออกมา ซึ่งจะมีรูปแบบ "439.00/ 2840 cms"
        raw_text = data_cell.get_text(strip=True)

        # 5. แยกข้อมูลส่วนหน้าเครื่องหมาย / ออกมา
        if "/" in raw_text:
            main_value = raw_text.split('/')[0].strip()
            # คัดกรองให้เหลือแต่ตัวเลขและจุดทศนิยม
            num = re.sub(r"[^\d.]", "", main_value)
            if num:
                return f"{num} cms" # คืนค่าเป็น "439.00 cms"

    except requests.exceptions.RequestException as e:
        print(f"เกิดข้อผิดพลาดในการดึง URL: {e}")
        return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาดระหว่างการวิเคราะห์ข้อมูล: {e}")
        return None

    print("Error: ไม่พบข้อมูลปริมาณน้ำในรูปแบบที่คาดไว้")
    return None

# ... (ฟังก์ชันอื่นๆ ที่เหลือในไฟล์คงไว้เหมือนเดิม) ...
