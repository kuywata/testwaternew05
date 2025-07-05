def get_inburi_river_data():
    """ดึงข้อมูลระดับน้ำและระดับตลิ่งจาก API ของ ThaiWater.net สำหรับสถานี C.35"""
    try:
        print(f"Fetching data from ThaiWater API for station C35...")
        response = requests.get(STATION_API_URL, timeout=15)
        response.raise_for_status() # เช็ค error http เช่น 404, 500

        # --- ส่วนแก้ไข เพิ่มการดักจับ JSON Error ---
        try:
            api_data = response.json()
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON. The response from the server is not valid JSON.")
            print("--- Server Response Text (First 500 chars) ---")
            print(response.text[:500]) # พิมพ์ 500 ตัวอักษรแรกของข้อมูลที่ได้รับ
            print("---------------------------------------------")
            return None
        # --- จบส่วนแก้ไข ---

        latest_data = api_data['data']['data'][-1]
        station_name_full = api_data['data']['station']['tele_station_name']
        water_level_str = latest_data['storage_water_level']
        bank_level_str = api_data['data']['station']['ground_level']

        print(f"Found station: {station_name_full}")
        print(f"  - Water Level: {water_level_str}")
        print(f"  - Bank Level: {bank_level_str}")

        if water_level_str is None or bank_level_str is None:
            print("Warning: Water level or bank level data is null.")
            return None

        water_level = float(water_level_str)
        bank_level = float(bank_level_str)
        overflow = water_level - bank_level

        return {
            "station": station_name_full,
            "water_level": water_level,
            "bank_level": bank_level,
            "overflow": overflow
        }

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        return None
    except (ValueError, IndexError, KeyError) as e:
        print(f"An error occurred while parsing the data: {e}")
        return None
