import requests

TELEGRAM_TOKEN = "9268038700:AAGEtH4cmpoQg7rzPs8h0APqB8-HO93ILz8"

def main():
    print("--- شروع تست تشخیصی ---")
    
    # ۱. بررسی اعتبار توکن
    print("1. در حال بررسی توکن ربات...")
    res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe").json()
    print(f"پاسخ تلگرام: {res}")
    if not res.get("ok"):
        print("❌ توکن نامعتبر است!")
        return
    print(f"✅ توکن معتبر است. نام ربات: {res['result']['first_name']}")

    # ۲. پاک کردن Webhook
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook")

    # ۳. دریافت پیام‌ها
    print("3. در حال دریافت پیام‌های جدید از تلگرام...")
    updates = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?timeout=5").json()
    
    messages = updates.get('result', [])
    print(f"تعداد پیام‌های دریافت شده: {len(messages)}")

    if messages:
        # علامت‌گذاری به عنوان خوانده شده
        last_update_id = messages[-1]["update_id"]
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}")
        
        for msg in messages:
            if "message" in msg and "text" in msg["message"]:
                chat_id = msg["message"]["chat"]["id"]
                text = msg["message"]["text"]
                print(f"پیام دریافت شده: '{text}' از چت {chat_id}")
                
                print("در حال ارسال جواب تست...")
                send_res = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": f"✅ تست موفق بود! پیام شما دریافت شد: {text}"}
                ).json()
                print(f"وضعیت ارسال: {send_res.get('ok')}")
    else:
        print("❌ هیچ پیامی در صف تلگرام وجود ندارد.")

if __name__ == "__main__":
    main()
