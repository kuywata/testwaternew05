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
        # เพิ่ม Headers เพื่อเลียนแบบ Browser จริง
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- จุดที่แก้ไข ---
        # เปลี่ยนจากการหา class เป็นการหา <table_第一個> ที่เจอในหน้า
        table = soup.find('table') 
        # -----------------
        
        if not table:
            print("ไม่พบตารางข้อมูลใดๆ ในหน้าเว็บ")
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
        
        with open('last_inburi_data.txt', 'w', encoding='utf-8') as f:
            json.dump(river_data, f, ensure_ascii=False, indent=2)
        print("\nบันทึกข้อมูลลง last_inburi_data.txt สำเร็จ")
    else:
        print("ไม่สามารถดึงข้อมูลได้")
