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

# ================= تشخیص الگوهای کندلی و شکست سطوح =================
def detect_price_action(opens, highs, lows, closes):
    if len(closes) < 25: return None, None, None, None
    
    lookback = 20
    recent_highs = highs[-lookback-1:-1]
    recent_lows = lows[-lookback-1:-1]
    resistance = max(recent_highs)
    support = min(recent_lows)
    
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    prev_o, prev_c = opens[-2], closes[-2]
    
    body = abs(c - o)
    upper_shadow = h - max(c, o)
    lower_shadow = min(c, o) - l
    
    pattern_name = None
    signal_type = None

    # ۱. تشخیص شکست سطح (Breakout/Breakdown) - مهم‌ترین بخش برای بازارهای شارپ
    if c < support:
        signal_type = "SELL"
        pattern_name = "Support Breakdown (شکست حمایت)"
    elif c > resistance:
        signal_type = "BUY"
        pattern_name = "Resistance Breakout (شکست مقاومت)"
        
    # ۲. تشخیص الگوهای کندلی برای تایید بیشتر
    else:
        # الگوی چکش (Hammer)
        if lower_shadow > 2 * body and upper_shadow < 0.2 * body and c > o:
            pattern_name = "Hammer (چکش)"
            signal_type = "BUY"
                
        # الگوی ستاره دنباله‌دار (Shooting Star)
        elif upper_shadow > 2 * body and lower_shadow < 0.2 * body and c < o:
            pattern_name = "Shooting Star (ستاره دنباله‌دار)"
            signal_type = "SELL"

        # الگوی پوشای صعودی (Bullish Engulfing)
        elif prev_c < prev_o and c > o and c > prev_o and o < prev_c:
            pattern_name = "Bullish Engulfing (پوشای صعودی)"
            signal_type = "BUY"
                
        # الگوی پوشای نزولی (Bearish Engulfing)
        elif prev_c > prev_o and c < o and c < prev_o and o > prev_c:
            pattern_name = "Bearish Engulfing (پوشای نزولی)"
            signal_type = "SELL"

        # الگوی مارابوزو (Marubozu) - کندل‌های با قدرت زیاد
        elif body > (h - l) * 0.9:
            if c > o:
                pattern_name = "Bullish Marubozu (مارابوزوی صعودی)"
                signal_type = "BUY"
            else:
                pattern_name = "Bearish Marubozu (مارابوزوی نزولی)"
                signal_type = "SELL"

    return pattern_name, signal_type, support, resistance

# ================= تحلیل اختصاصی =================
def analyze_coin(coin, tf="5min"):
    try:
        tf_map = {"15m": "15min", "1h": "1hour", "4h": "4hour", "1d": "1day", "5m": "5min"}
        tf = tf_map.get(tf.lower(), tf.lower())
        if tf not in ["5min", "15min", "1hour", "4hour", "1day"]: tf = "5min"

        url = f"https://api.kucoin.com/api/v1/market/candles?type={tf}&symbol={coin.upper()}-USDT"
        response = requests.get(url, timeout=10).json()
        
        if response.get("code") != "200000":
            return f"❌ ارز {coin} در صرافی یافت نشد."
            
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
            
            position = "⚪ خنثی (بدون سیگنال)"
            if signal_type == "BUY": position = "🟢 <b>سیگنال خرید (BUY)</b>"
            elif signal_type == "SELL": position = "🔴 <b>سیگنال فروش (SELL)</b>"
                
            msg = (f"📊 <b>تحلیل پرایس اکشن {coin.upper()}/USDT (تایم‌فریم {tf})</b>\n"
                   f"━━━━━━━━━━━━━━━\n"
                   f"🎯 <b>موقعیت: {position}</b>\n\n"
                   f"💰 قیمت فعلی: {current_price:.4f}\n"
                   f"🕯️ الگو: {pattern_name if pattern_name else 'الگوی خاصی یافت نشد'}\n"
                   f"🛡 حمایت: {support:.4f}\n"
                   f"🚧 مقاومت: {resistance:.4f}\n\n"
                   f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            return msg
        else:
            return f"❌ داده کافی نیست."
    except Exception as e:
        return f"❌ خطا در تحلیل: {e}"

# ================= چک کردن پیام‌ها =================
def check_telegram_commands():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?timeout=5"
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return
        data = response.json()
        
        if data.get("ok") and data.get("result"):
            updates = data["result"]
            last_update_id = updates[-1]["update_id"]
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}", timeout=5)
            
            for msg in updates:
                if "message" in msg and "text" in msg["message"]:
                    text = msg["message"]["text"].strip().upper()
                    user_chat_id = msg["message"]["chat"]["id"]
                    
                    if text == "/START":
                        send_telegram_msg(user_chat_id, "👋 سلام!\nاسم ارز رو بفرست (مثلا: BTC).\nبرای تایم‌فریم خاص: BTC 4h")
                        continue
                    
                    parts = text.split()
                    coin = parts[0]
                    tf = "5min" if len(parts) == 1 else parts[1]
                    
                    send_telegram_msg(user_chat_id, f"⏳ پیام شما ({coin} {tf}) دریافت شد. در حال تحلیل...")
                    result = analyze_coin(coin, tf)
                    send_telegram_msg(user_chat_id, result)
    except Exception as e:
        print(f">>> Error: {e}")

# ================= حلقه اسکن بازار (۳۰ ارز برتر) =================
def scan_market():
    # لیست ۳۰ ارز برتر برای اسکن
    watch_list = [
        "BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "LTC", "LINK", "MATIC",
        "DOT", "AVAX", "SHIB", "TRX", "UNI", "ATOM", "ETC", "XLM", "BCH", "FIL",
        "APT", "ARB", "OP", "SUI", "SEI", "TIA", "INJ", "NEAR", "GRT", "AAVE"
    ]
    print(f">>> Scanning {len(watch_list)} coins for Breakouts/Candles...")
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
                        msg = (f"🟢 <b>BUY SIGNAL: {coin}</b>\n\n"
                               f"🕯️ Pattern: {pattern_name}\n"
                               f"💰 Price: {current_price:.4f}\n"
                               f"🚧 Resistance: {resistance:.4f}\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(CHAT_ID, msg)
                        print(f">>> Sent BUY signal for {coin}.")
                        
                    elif signal_type == "SELL":
                        msg = (f"🔴 <b>SELL SIGNAL: {coin}</b>\n\n"
                               f"🕯️ Pattern: {pattern_name}\n"
                               f"💰 Price: {current_price:.4f}\n"
                               f"🛡 Support: {support:.4f}\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(CHAT_ID, msg)
                        print(f">>> Sent SELL signal for {coin}.")
        except Exception as e:
            pass
        time.sleep(0.3)

if __name__ == "__main__":
    check_telegram_commands()
    scan_market()
