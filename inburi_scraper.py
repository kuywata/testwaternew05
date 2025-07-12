import requests
from bs4 import BeautifulSoup
import json

# --- ค่าคงที่ ---
URL = "https://singburi.thaiwater.net/wl"
STATION_NAME_TO_FIND = "อินทร์บุรี"

def get_inburi_data():
    """
    ดึงข้อมูลระดับน้ำของสถานีอินทร์บุรีจากตาราง HTML
    """
    try:
        print(f"กำลังดึงข้อมูลจาก: {URL}")
        # ใช้ requests เพื่อดาวน์โหลดหน้าเว็บ
        response = requests.get(URL, timeout=15)
        response.raise_for_status() # ตรวจสอบว่าสำเร็จหรือไม่
        
        # ใช้ BeautifulSoup เพื่ออ่านข้อมูล HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # ค้นหาตารางข้อมูล
        table = soup.find('table', class_='table')
        if not table:
            print("ไม่พบตารางข้อมูลในหน้าเว็บ")
            return None
            
        # ค้นหาทุกแถวใน tbody ของตาราง
        for row in table.find('tbody').find_all('tr'):
            # แยกข้อมูลแต่ละคอลัมน์ (td)
            cells = row.find_all('td')
            
            # ตรวจสอบว่าใช่แถวของสถานี "อินทร์บุรี" หรือไม่
            if cells and STATION_NAME_TO_FIND in cells[1].text:
                print(f"พบข้อมูลของสถานี: {STATION_NAME_TO_FIND}")
                
                # ดึงข้อมูลจากแต่ละคอลัมน์ตามลำดับในภาพ
                water_level = float(cells[2].text.strip())
                bank_level = float(cells[3].text.strip())
                status = cells[4].text.strip()
                diff_to_bank = float(cells[5].text.strip().replace('ต่ำกว่าตลิ่ง (ม.)','').strip())
                time = cells[6].text.strip()

                # จัดข้อมูลในรูปแบบ dictionary
                data = {
                    "station_name": cells[1].text.strip().replace('\n', ' '),
                    "water_level": water_level,
                    "bank_level": bank_level,
                    "status": status,
                    "diff_to_bank": diff_to_bank,
                    "time": time,
                    "source": URL
                }
                return data

        print(f"ไม่พบข้อมูลของสถานี '{STATION_NAME_TO_FIND}' ในตาราง")
        return None

    except requests.exceptions.RequestException as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
        return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาดไม่คาดคิด: {e}")
        return None


if __name__ == '__main__':
    river_data = get_inburi_data()
    
    if river_data:
        print("\nข้อมูลที่ดึงได้:")
        print(json.dumps(river_data, indent=2, ensure_ascii=False))
        
        # บันทึกข้อมูลลงไฟล์ (เหมือนเดิม)
        with open('last_inburi_data.txt', 'w', encoding='utf-8') as f:
            json.dump(river_data, f, ensure_ascii=False, indent=2)
        print("\nบันทึกข้อมูลลง last_inburi_data.txt สำเร็จ")
    else:
        print("ไม่สามารถดึงข้อมูลได้")
