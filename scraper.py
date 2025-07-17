import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz

# --- ค่าคงที่ ---
URL = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')
TIMEZONE_THAILAND = pytz.timezone('Asia/Bangkok')
HISTORICAL_LOG_FILE = 'historical_log.csv'
LAST_DATA_FILE = 'last_data.txt'


def get_water_data(timeout=30):
    """
    ดึงข้อมูลปริมาณน้ำโดยใช้ 'ปริมาณน้ำ' เป็นจุดอ้างอิง และเพิ่ม User-Agent
    เพื่อปลอมตัวเป็นเบราว์เซอร์ ทำให้ได้รับข้อมูลเว็บฉบับเต็ม
    """
    try:
        # **ส่วนที่เพิ่มเข้ามา: ปลอมตัวเป็นเบราว์เซอร์**
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # เพิ่ม headers เข้าไปในคำขอ
        response = requests.get(URL, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. ค้นหา <td> ที่มีข้อความว่า "ปริมาณน้ำ"
        label_cell = soup.find('td', string='ปริมาณน้ำ')

        if not label_cell:
            print("Error: ไม่พบป้ายกำกับ 'ปริมาณน้ำ' ในหน้าเว็บ (อาจเป็นเพราะ HTML เปลี่ยนแปลง)")
            return None

        # 2. ข้อมูลตัวเลขจะอยู่ใน <td> ถัดไป (next sibling)
        data_cell = label_cell.find_next_sibling('td')

        if not data_cell:
            print("Error: ไม่พบช่องข้อมูลที่อยู่ถัดจากป้ายกำกับ")
            return None

        # 3. ดึงข้อความออกมา
        raw_text = data_cell.get_text(strip=True)
        
        # 4. แยกข้อมูลส่วนหน้าเครื่องหมาย / ออกมา
        if "/" in raw_text:
            main_value = raw_text.split('/')[0].strip()
            num = re.sub(r"[^\d.]", "", main_value)
            if num:
                return f"{num} cms"

    except requests.exceptions.RequestException as e:
        print(f"เกิดข้อผิดพลาดในการดึง URL: {e}")
        return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาดระหว่างการวิเคราะห์ข้อมูล: {e}")
        return None

    print("Error: ไม่พบข้อมูลปริมาณน้ำในรูปแบบที่คาดไว้")
    return None


def get_historical_data(target_date):
    if not os.path.exists(HISTORICAL_LOG_FILE):
        return None
    start = target_date - timedelta(hours=12)
    end = target_date + timedelta(hours=12)
    best, best_diff = None, timedelta.max
    with open(HISTORICAL_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                ts, val = line.strip().split(",", 1)
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = TIMEZONE_THAILAND.localize(dt)
                diff = abs(target_date - dt)
                if start <= dt <= end and diff < best_diff:
                    best_diff, best = diff, val
            except ValueError:
                continue
    return best


def append_to_historical_log(now, data):
    with open(HISTORICAL_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{now.isoformat()},{data}\n")


def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("Missing LINE credentials.")
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
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        print("ส่งข้อความ LINE สำเร็จ:", resp.status_code)
    except Exception as e:
        print("ส่งข้อความ LINE ไม่สำเร็จ:", e)


def main():
    last = ''
    if os.path.exists(LAST_DATA_FILE):
        last = open(LAST_DATA_FILE, 'r', encoding='utf-8').read().strip()

    current = get_water_data()
    if not current:
        print("ไม่สามารถดึงค่าปัจจุบันได้ จึงไม่มีการแจ้งเตือน")
        return

    print("ค่าปัจจุบัน:", current)
    now_th = datetime.now(TIMEZONE_THAILAND)

    hist = get_historical_data(now_th - timedelta(days=365))
    hist_str = f"\n\nเทียบปีที่แล้ว ({(now_th - timedelta(days=365)).strftime('%d/%m/%Y')}): {hist}" if hist else ''

    msg = (
        f"🌊 แจ้งเตือนปริมาณน้ำ เขื่อนเจ้าพระยา\n"
        f"━━━━━━━━━━\n"
        f"✅ ปัจจุบัน: {current}\n"
        f"⬅️ เดิม: {last or 'ไม่พบ'}\n"
        f"🗓️ {now_th.strftime('%d/%m/%Y %H:%M')}"
        f"{hist_str}"
    )
    send_line_message(msg)

    with open(LAST_DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(current)
    append_to_historical_log(now_th, current)
    print("อัปเดต historical log เรียบร้อย")


if __name__ == "__main__":
    main()
