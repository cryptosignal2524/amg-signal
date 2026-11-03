import requests
import time
from datetime import datetime

# 🔐 توکن
TELEGRAM_TOKEN = "9268038700:AAGEtH4cmpoQg7rzPs8h0APqB8-HO93ILz8"
CHAT_ID = "@AMG_Signals"

def send_telegram_msg(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

# ================= تشخیص الگوهای کندلی و سطوح =================
def detect_price_action(opens, highs, lows, closes):
    if len(closes) < 25: return None, None, None
    
    # محاسبه سطوح حمایت و مقاومت (سقف و کف 20 کندل اخیر)
    lookback = 20
    recent_highs = highs[-lookback-1:-1]
    recent_lows = lows[-lookback-1:-1]
    resistance = max(recent_highs)
    support = min(recent_lows)
    
    # داده‌های کندل آخر و قبلی
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    prev_o, prev_c = opens[-2], closes[-2]
    
    body = abs(c - o)
    upper_shadow = h - max(c, o)
    lower_shadow = min(c, o) - l
    prev_body = abs(prev_c - prev_o)
    
    # فاصله قیمت از سطوح (1 درصد)
    near_support = (c - support) / support < 0.01
    near_resistance = (resistance - c) / resistance < 0.01
    
    pattern_name = None
    signal_type = None

    # 1. الگوی چکش (Hammer) - در حمایت
    if lower_shadow > 2 * body and upper_shadow < 0.2 * body and c > o:
        pattern_name = "Hammer (چکش)"
        if near_support:
            signal_type = "BUY"
            
    # 2. الگوی ستاره دنباله‌دار (Shooting Star) - در مقاومت
    elif upper_shadow > 2 * body and lower_shadow < 0.2 * body and c < o:
        pattern_name = "Shooting Star (ستاره دنباله‌دار)"
        if near_resistance:
            signal_type = "SELL"

    # 3. الگوی پوشای صعودی (Bullish Engulfing) - در حمایت
    elif prev_c < prev_o and c > o and c > prev_o and o < prev_c:
        pattern_name = "Bullish Engulfing (پوشای صعودی)"
        if near_support:
            signal_type = "BUY"
            
    # 4. الگوی پوشای نزولی (Bearish Engulfing) - در مقاومت
    elif prev_c > prev_o and c < o and c < prev_o and o > prev_c:
        pattern_name = "Bearish Engulfing (پوشای نزولی)"
        if near_resistance:
            signal_type = "SELL"

    # 5. الگوی مارابوزو (Marubozu) - کندل با قدرت زیاد
    elif body > (h - l) * 0.9:
        if c > o:
            pattern_name = "Bullish Marubozu (مارابوزوی صعودی)"
            if near_support: signal_type = "BUY"
        else:
            pattern_name = "Bearish Marubozu (مارابوزوی نزولی)"
            if near_resistance: signal_type = "SELL"

    return pattern_name, signal_type, support, resistance

# ================= تحلیل اختصاصی =================
def analyze_coin(coin, tf="5min"):
    try:
        url = f"https://api.kucoin.com/api/v1/market/candles?type={tf}&symbol={coin}-USDT"
        response = requests.get(url, timeout=10).json()
        
        if response.get("code") != "200000":
            return f"❌ ارز {coin} یافت نشد."
            
        data = response.get("data", [])
        if not data: return f"❌ داده‌ای برای {coin} نیست."
            
        data.reverse()
        opens = [float(item[1]) for item in data]
        closes = [float(item[2]) for item in data]
        highs = [float(item[3]) for item in data]
        lows = [float(item[4]) for item in data]
        
        if len(closes) > 25:
            current_price = closes[-1]
            pattern_name, signal_type, support, resistance = detect_price_action(opens, highs, lows, closes)
            
            position = "⚪ خنثی (بدون سیگنال روی سطوح)"
            
            if signal_type == "BUY":
                position = "🟢 <b>سیگنال خرید (BUY)</b>"
            elif signal_type == "SELL":
                position = "🔴 <b>سیگنال فروش (SELL)</b>"
                
            msg = (f"📊 <b>تحلیل پرایس اکشن {coin}/USDT (تایم‌فریم {tf})</b>\n"
                   f"━━━━━━━━━━━━━━━\n"
                   f"🎯 <b>موقعیت: {position}</b>\n\n"
                   f"💰 قیمت فعلی: {current_price:.4f}\n"
                   f"🕯️ الگوی شناسایی شده: {pattern_name if pattern_name else 'الگوی معتبری یافت نشد'}\n"
                   f"🛡 سطح حمایت (Support): {support:.4f}\n"
                   f"🚧 سطح مقاومت (Resistance): {resistance:.4f}\n\n"
                   f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            return msg
        else:
            return f"❌ داده کافی برای تحلیل {coin} وجود ندارد."
    except Exception as e:
        return f"❌ خطا: {e}"

# ================= چک کردن پیام‌های کاربران =================
def check_telegram_commands():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?timeout=5"
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return
        data = response.json()
        
        if data.get("ok") and data.get("result"):
            updates = data["result"]
            last_update_id = None
            for msg in updates:
                last_update_id = msg["update_id"]
                if "message" in msg and "text" in msg["message"]:
                    text = msg["message"]["text"].strip().upper()
                    user_chat_id = msg["message"]["chat"]["id"]
                    
                    if text == "/START":
                        send_telegram_msg(user_chat_id, "👋 سلام!\nاسم ارز رو بفرست تا چارت و کندل‌هاش رو تحلیل کنم (مثلا: BTC).")
                        continue
                    
                    parts = text.split()
                    if len(parts) == 1 and text.isalnum() and len(text) <= 6:
                        send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل پرایس اکشن {text} (تایم‌فریم 5m)...")
                        result = analyze_coin(text, "5min")
                        send_telegram_msg(user_chat_id, result)
                    
                    elif len(parts) == 2:
                        coin = parts[0]
                        tf_input = parts[1].lower()
                        tf_map = {"15m": "15min", "1h": "1hour", "4h": "4hour", "1d": "1day"}
                        tf = tf_map.get(tf_input)
                        if tf:
                            send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل پرایس اکشن {coin} در تایم‌فریم {tf}...")
                            result = analyze_coin(coin, tf)
                            send_telegram_msg(user_chat_id, result)
                        else:
                            send_telegram_msg(user_chat_id, "❌ تایم‌فریم نامعتبر است. از 15m، 1h، 4h یا 1d استفاده کنید.")
            
            if last_update_id:
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}", timeout=5)
    except Exception as e:
        print(f">>> Error: {e}")

# ================= حلقه اسکن بازار =================
def scan_market():
    watch_list = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "LTC", "LINK", "MATIC"]
    print(f">>> Scanning {len(watch_list)} coins for Price Action Signals...")
    for coin in watch_list:
        try:
            url = f"https://api.kucoin.com/api/v1/market/candles?type=5min&symbol={coin}-USDT"
            response = requests.get(url, timeout=10).json()
            if response.get("code") == "200000":
                data = response.get("data", [])
                data.reverse()
                opens = [float(item[1]) for item in data]
                closes = [float(item[2]) for item in data]
                highs = [float(item[3]) for item in data]
                lows = [float(item[4]) for item in data]
                
                if len(closes) > 25:
                    current_price = closes[-1]
                    pattern_name, signal_type, support, resistance = detect_price_action(opens, highs, lows, closes)
                    
                    if signal_type == "BUY":
                        msg = (f"🟢 <b>PRICE ACTION BUY: {coin}</b>\n\n"
                               f"🕯️ Pattern: {pattern_name} at Support\n"
                               f"💰 Price: {current_price:.4f}\n"
                               f"🛡 Support: {support:.4f}\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(CHAT_ID, msg)
                    elif signal_type == "SELL":
                        msg = (f"🔴 <b>PRICE ACTION SELL: {coin}</b>\n\n"
                               f"🕯️ Pattern: {pattern_name} at Resistance\n"
                               f"💰 Price: {current_price:.4f}\n"
                               f"🚧 Resistance: {resistance:.4f}\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(CHAT_ID, msg)
        except Exception as e:
            pass
        time.sleep(0.3)

if __name__ == "__main__":
    check_telegram_commands()
    scan_market()
