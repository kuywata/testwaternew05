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
    ดึงข้อมูลปริมาณน้ำโดยการค้นหาจากข้อความอ้างอิงที่ตายตัว ("ที่ท้ายเขื่อนเจ้าพระยา")
    แล้วจึงค้นหาข้อมูลจากโครงสร้าง HTML ที่อยู่ถัดไป ทำให้มีความแม่นยำและเสถียรสูง
    """
    try:
        response = requests.get(URL, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        anchor_tag = soup.find('strong', string='ที่ท้ายเขื่อนเจ้าพระยา')
        if not anchor_tag:
            print("Error: ไม่พบจุดอ้างอิง 'ที่ท้ายเขื่อนเจ้าพระยา' ในหน้าเว็บ")
            return None

        data_row = anchor_tag.find_parent('tr').find_next_sibling('tr')
        if not data_row:
            print("Error: ไม่พบแถวของข้อมูลที่อยู่ถัดจากจุดอ้างอิง")
            return None

        data_cell = data_row.find('td', class_='text_bold')
        if not data_cell:
            print("Error: ไม่พบช่องของข้อมูล (td.text_bold)")
            return None

        raw_text = data_cell.get_text(strip=True)
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
