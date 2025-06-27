import requests
import os

# ไม่ต้องใช้ re, json, BeautifulSoup ในเวอร์ชันทดสอบนี้

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.environ.get('LINE_TARGET_ID')

def send_line_message(message):
    """
    ฟังก์ชันสำหรับส่งข้อความแจ้งเตือนผ่าน LINE Messaging API
    """
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("LINE credentials are not set in GitHub Secrets. Cannot send message.")
        return

    print(f"Attempting to send message to: {LINE_TARGET_ID}")
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
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        print("LINE message sent successfully! API Response:", response.text)
    except requests.exceptions.RequestException as e:
        print("!!! FAILED to send LINE message !!!")
        if e.response:
            print(f"Status Code: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
        else:
            print(f"An error occurred without a response: {e}")

def main():
    """
    ฟังก์ชันหลัก (เวอร์ชันทดสอบการส่ง LINE)
    """
    print("--- STARTING NOTIFICATION TEST ---")

    # สร้างข้อความทดสอบ
    test_message = "นี่คือข้อความทดสอบจากระบบแจ้งเตือนอัตโนมัติของคุณ หากคุณเห็นข้อความนี้ แสดงว่าการเชื่อมต่อกับ LINE ทำงานถูกต้อง! ✅"

    # สั่งส่งข้อความทดสอบโดยตรง
    send_line_message(test_message)

    print("--- FINISHED NOTIFICATION TEST ---")

if __name__ == "__main__":
    main()
