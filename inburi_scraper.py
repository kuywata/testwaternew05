def get_inburi_river_data():
    """ดึงข้อมูลระดับน้ำ, ระดับตลิ่ง และคำนวณส่วนต่างจากสถานี C.35 อินทร์บุรี"""
    try:
        print(f"Fetching data from RID website for station {STATION_NAME}...")
        # เพิ่ม verify=False เพื่อข้ามการตรวจสอบ SSL Certificate
        response = requests.get(STATION_URL, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # ค้นหาตารางข้อมูลทั้งหมด
        tables = soup.find_all('table', class_='table-striped')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                # เช็คว่าแถวนี้คือสถานี C.35 หรือไม่
                if cells and STATION_NAME in cells[0].text:
                    station_name_full = cells[0].text.strip()
                    water_level_str = cells[1].text.strip()
                    bank_level_str = cells[3].text.strip() # ระดับตลิ่งคือคอลัมน์ที่ 4

                    print(f"Found station: {station_name_full}")
                    print(f"  - Water Level: {water_level_str}")
                    print(f"  - Bank Level: {bank_level_str}")
                    
                    # แปลงเป็นตัวเลข
                    water_level = float(water_level_str)
                    bank_level = float(bank_level_str)
                    
                    # คำนวณส่วนต่างจากตลิ่ง
                    overflow = water_level - bank_level
                    
                    # สร้าง Dictionary เพื่อส่งข้อมูลกลับ
                    return {
                        "station": station_name_full,
                        "water_level": water_level,
                        "bank_level": bank_level,
                        "overflow": overflow
                    }
        
        print(f"Could not find station {STATION_NAME} in the tables.")
        return None

    except (requests.exceptions.RequestException, ValueError, IndexError) as e:
        print(f"An error occurred in get_inburi_river_data: {e}")
        return None
