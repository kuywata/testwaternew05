import requests
from bs4 import BeautifulSoup
import os

URL = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')

def get_water_data():
    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status()

        #---- ส่วนที่เพิ่มเข้ามาเพื่อตรวจสอบ ----
        print("--- START OF HTML CONTENT ---")
        print(response.text)
        print("--- END OF HTML CONTENT ---")
        #------------------------------------

        soup = BeautifulSoup(response.content, 'html.parser')
        target_row = soup.find(lambda tag: tag.name == 'td' and 'ท้ายเขื่อนเจ้าพระยา' in tag.text)

        if target_row:
            data_tds = target_row.find_next_siblings('td')
            if len(data_tds) > 0:
                water_level_text = data_tds[0].get_text(strip=True)
                return water_level_text
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def send_line_message(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials are not set. Cannot send message.")
        return
    url = 'https://api.line.me/v2/bot/message/push'
    headers = { 'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}' }
    payload = { 'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}] }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("LINE message sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending LINE message: {e.response.text if e.response else 'No response'}")

def main():
    last_data_file = 'last_data.txt'
    last_data = ''
    if os.path.exists(last_data_file):
        with open(last_data_file, 'r', encoding='utf-8') as f:
            last_data = f.read().strip()
    current_data = get_water_data()
    if current_data:
        print(f"Current data: {current_data}")
        print(f"Last saved data: {last_data}")
        if current_data != last_data:
            print("Data has changed! Sending notification...")
            message = f"อัปเดต! 🚨\nปริมาณน้ำท้ายเขื่อนเจ้าพระยา (จ.ชัยนาท)\n\n" \
                      f"ค่าปัจจุบัน: {current_data}\n" \
                      f"ค่าเดิม: {last_data if last_data else 'ยังไม่มีข้อมูลก่อนหน้า'}"
            send_line_message(message)
            with open(last_data_file, 'w', encoding='utf-8') as f:
                f.write(current_data)
        else:
            print("Data has not changed.")
    else:
        print("Could not retrieve current data.")

if __name__ == "__main__":
    main()
