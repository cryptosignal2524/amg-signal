import requests
import time
from datetime import datetime

# 🔐 توکن مستقیماً اینجا قرار گرفت
TELEGRAM_TOKEN = "9268038700:AAGEtH4cmpoQg7rzPs8h0APqB8-HO93ILz8"
CHAT_ID = "@AMG_Signals" # نام کانال شما

def send_telegram_msg(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

def send_timeframe_menu(chat_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "⚡ اسکلپ (15m)", "callback_data": "menu_tf_15min"},
                {"text": "⏱ 1 ساعته (1H)", "callback_data": "menu_tf_1hour"}
            ],
            [
                {"text": "⏳ 4 ساعته (4H)", "callback_data": "menu_tf_4hour"},
                {"text": "📅 روزانه (1D)", "callback_data": "menu_tf_1day"}
            ]
        ]
    }
    payload = {
        "chat_id": chat_id, 
        "text": "لطفاً تایم‌فریم مورد نظر برای تحلیل را انتخاب کنید:", 
        "reply_markup": keyboard
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending menu: {e}")

# ================= دریافت ۵۰ ارز برتر =================
def get_top_50_coins():
    try:
        url = "https://api.kucoin.com/api/v1/market/allTickers"
        response = requests.get(url, timeout=10).json()
        if response.get("code") == "200000":
            tickers = response["data"]["ticker"]
            usdt_pairs = [t for t in tickers if t["symbol"].endswith("-USDT")]
            usdt_pairs.sort(key=lambda x: float(x["volValue"]), reverse=True)
            return [t["symbol"].replace("-USDT", "") for t in usdt_pairs[:50]]
    except Exception as e:
        print(f"Error fetching top coins: {e}")
    return []

# ================= محاسبات اندیکاتورها =================
def calc_ema(data, period):
    k = 2 / (period + 1)
    ema_val = data[0]
    for price in data[1:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val

def calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1: return 0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return sum(trs[-period:]) / period

# ================= تشخیص الگوهای کندلی =================
def detect_patterns(opens, highs, lows, closes, volumes):
    if len(closes) < 20: return None, None
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    prev_o, prev_c = opens[-2], closes[-2]
    body = abs(c - o)
    upper_shadow = h - max(c, o)
    lower_shadow = min(c, o) - l
    
    if body > (h - l) * 0.9:
        if c > o: return "Bullish Marubozu", "BUY"
        else: return "Bearish Marubozu", "SELL"
    if lower_shadow > 2 * body and upper_shadow < 0.2 * body and c > o:
        return "Hammer", "BUY"
    if upper_shadow > 2 * body and lower_shadow < 0.2 * body and c < o:
        return "Shooting Star", "SELL"
    if prev_c < prev_o and c > o and c > prev_o and o < prev_c:
        return "Bullish Engulfing", "BUY"
    if prev_c > prev_o and c < o and c < prev_o and o > prev_c:
        return "Bearish Engulfing", "SELL"
    return None, None

# ================= تحلیل تایم‌فریم انتخابی =================
def analyze_single_tf(coin, tf):
    try:
        url = f"https://api.kucoin.com/api/v1/market/candles?type={tf}&symbol={coin}-USDT"
        response = requests.get(url, timeout=10).json()
        if response.get("code") == "200000":
            data = response.get("data", [])
            data.reverse()
            opens = [float(item[1]) for item in data]
            closes = [float(item[2]) for item in data]
            highs = [float(item[3]) for item in data]
            lows = [float(item[4]) for item in data]
            volumes = [float(item[5]) for item in data]
            
            if len(closes) > 50:
                current_price = closes[-1]
                current_volume = volumes[-1]
                avg_volume = sum(volumes[-20:]) / 20
                ema50 = calc_ema(closes, 50)
                atr = calc_atr(highs, lows, closes)
                
                pattern_name, signal_type = detect_patterns(opens, highs, lows, closes, volumes)
                
                position = "⚪ خنثی (Neutral)"
                tp_sl_info = ""
                
                if signal_type == "BUY" and current_price > ema50:
                    if current_volume > avg_volume * 1.2:
                        position = "🟢 <b>سیگنال خرید (BUY)</b>"
                        sl = current_price - (atr * 1.5)
                        tp = current_price + (atr * 3.0)
                        tp_sl_info = f"\n🎯 <b>Take Profit:</b> {tp:.4f}\n🛑 <b>Stop Loss:</b> {sl:.4f}"
                elif signal_type == "SELL" and current_price < ema50:
                    if current_volume > avg_volume * 1.2:
                        position = "🔴 <b>سیگنال فروش (SELL)</b>"
                        sl = current_price + (atr * 1.5)
                        tp = current_price - (atr * 3.0)
                        tp_sl_info = f"\n🎯 <b>Take Profit:</b> {tp:.4f}\n🛑 <b>Stop Loss:</b> {sl:.4f}"
                elif pattern_name:
                    position = "🟡 الگو دیده شد ولی تاییدیه روند/حجم ندارد"

                msg = (f"📊 <b>تحلیل {coin}/USDT (تایم‌فریم {tf})</b>\n"
                       f"━━━━━━━━━━━━━━━\n"
                       f"🎯 <b>موقعیت: {position}</b>\n\n"
                       f"💰 قیمت فعلی: {current_price:.4f}\n"
                       f"🕯️ الگوی شناسایی شده: {pattern_name if pattern_name else 'الگوی خاصی یافت نشد'}\n"
                       f"📈 روند (EMA50): {'صعودی ✅' if current_price > ema50 else 'نزولی ❌'}\n"
                       f"📊 حجم: {current_volume:.0f} (میانگین: {avg_volume:.0f}){tp_sl_info}\n\n"
                       f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                return msg
    except Exception as e:
        return f"❌ خطا در تحلیل {coin}: {e}"
    return f"❌ ارز {coin} در صرافی یافت نشد یا داده کافی ندارد."

# ================= چک کردن پیام‌ها و دکمه‌ها =================
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
                
                # ۱. بررسی پیام‌های متنی
                if "message" in msg and "text" in msg["message"]:
                    text = msg["message"]["text"].strip().upper()
                    user_chat_id = msg["message"]["chat"]["id"]
                    
                    if text == "/START":
                        send_timeframe_menu(user_chat_id)
                        continue
                    
                    # اگر کاربر به پیام درخواست نام ارز پاسخ داده باشد (با ForceReply)
                    if "reply_to_message" in msg["message"]:
                        original_text = msg["message"]["reply_to_message"]["text"]
                        tf = None
                        if "اسکلپ" in original_text: tf = "15min"
                        elif "1 ساعته" in original_text: tf = "1hour"
                        elif "4 ساعته" in original_text: tf = "4hour"
                        elif "روزانه" in original_text: tf = "1day"
                        
                        if tf and text.isalnum():
                            send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل {text} در تایم‌فریم {tf}...")
                            result = analyze_single_tf(text, tf)
                            send_telegram_msg(user_chat_id, result)
                            continue
                    
                    # اگر کاربر بدون منو اسم ارز را فرستاد (مثلا BTC)
                    if text.isalnum() and len(text) <= 6:
                        send_telegram_msg(user_chat_id, f"شما ارز <b>{text}</b> را انتخاب کردید. لطفا یک تایم‌فریم را از منوی زیر انتخاب کنید:")
                        # در اینجا از همان منو استفاده می‌کنیم
                        keyboard = {
                            "inline_keyboard": [
                                [
                                    {"text": "⚡ اسکلپ (15m)", "callback_data": f"analyze_{text}_15min"},
                                    {"text": "⏱ 1 ساعته (1H)", "callback_data": f"analyze_{text}_1hour"}
                                ],
                                [
                                    {"text": "⏳ 4 ساعته (4H)", "callback_data": f"analyze_{text}_4hour"},
                                    {"text": "📅 روزانه (1D)", "callback_data": f"analyze_{text}_1day"}
                                ]
                            ]
                        }
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": user_chat_id, "text": "تایم‌فریم مورد نظر را انتخاب کنید:", "reply_markup": keyboard})

                
                # ۲. بررسی کلیک روی دکمه‌های شیشه‌ای
                elif "callback_query" in msg:
                    callback_query = msg["callback_query"]
                    user_chat_id = callback_query["message"]["chat"]["id"]
                    callback_id = callback_query["id"]
                    data_str = callback_query["data"] 
                    
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_id})
                    
                    if data_str.startswith("menu_tf_"):
                        tf = data_str.split("_")[2]
                        tf_persian = {"15min": "اسکلپ", "1hour": "۱ ساعته", "4hour": "۴ ساعته", "1day": "روزانه"}
                        tf_name = tf_persian.get(tf, tf)
                        
                        # درخواست نام ارز با قابلیت ForceReply
                        url_ask = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                        payload_ask = {
                            "chat_id": user_chat_id,
                            "text": f"تایم‌فریم <b>{tf_name}</b> انتخاب شد.\nلطفا نام ارز را ارسال کنید (مثال: BTC):",
                            "parse_mode": "HTML",
                            "reply_markup": {"force_reply": True}
                        }
                        requests.post(url_ask, json=payload_ask)
                        
                    elif data_str.startswith("analyze_"):
                        parts = data_str.split("_")
                        if len(parts) == 3:
                            coin = parts[1]
                            tf = parts[2]
                            send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل {coin} در تایم‌فریم {tf}...")
                            result = analyze_single_tf(coin, tf)
                            send_telegram_msg(user_chat_id, result)
            
            if last_update_id:
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}", timeout=5)
    except Exception as e:
        print(f">>> Error: {e}")

# ================= دریافت روند در تایم‌فریم‌های مختلف =================
def get_trend(coin, timeframe):
    try:
        url = f"https://api.kucoin.com/api/v1/market/candles?type={timeframe}&symbol={coin}-USDT"
        response = requests.get(url, timeout=10).json()
        if response.get("code") == "200000":
            data = response.get("data", [])
            data.reverse()
            closes = [float(item[2]) for item in data]
            if len(closes) > 50:
                ema50 = calc_ema(closes, 50)
                current_price = closes[-1]
                return "صعودی 🟢" if current_price > ema50 else "نزولی 🔴", current_price, ema50
    except Exception:
        pass
    return "نامشخص ⚪", 0, 0

# ================= حلقه اصلی (اسکن خودکار ۵۰ ارز) =================
def scan_market():
    watch_list = get_top_50_coins()
    if not watch_list: watch_list = ["BTC", "ETH", "SOL", "XRP", "ADA"]
        
    print(f">>> Scanning {len(watch_list)} coins...")
    for coin in watch_list:
        try:
            trend_1d, _, _ = get_trend(coin, "1day")
            time.sleep(0.1)
            trend_4h, _, _ = get_trend(coin, "4hour")
            time.sleep(0.1)
            
            if "نامشخص" in trend_1d or "نامشخص" in trend_4h: continue
            if trend_1d != trend_4h: continue

            url = f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={coin}-USDT"
            response = requests.get(url, timeout=10).json()
            
            if response.get("code") == "200000":
                data = response.get("data", [])
                data.reverse()
                opens = [float(item[1]) for item in data]
                closes = [float(item[2]) for item in data]
                highs = [float(item[3]) for item in data]
                lows = [float(item[4]) for item in data]
                volumes = [float(item[5]) for item in data]
                
                if len(closes) > 50:
                    current_price = closes[-1]
                    current_volume = volumes[-1]
                    avg_volume = sum(volumes[-20:]) / 20
                    atr = calc_atr(highs, lows, closes)
                    
                    pattern_name, signal_type = detect_patterns(opens, highs, lows, closes, volumes)
                    
                    if pattern_name and current_volume > avg_volume * 1.2:
                        if signal_type == "BUY" and trend_1d == "صعودی 🟢":
                            sl = current_price - (atr * 1.5)
                            tp = current_price + (atr * 3.0)
                            msg = (f"🚀 <b>BUY SIGNAL: {coin}</b>\n\n"
                                   f"🌍 1D Trend: UP | ⏳ 4H Trend: UP\n"
                                   f"🕯️ Pattern: {pattern_name}\n"
                                   f"💰 Price: {current_price:.4f}\n"
                                   f"🎯 TP: {tp:.4f} | 🛑 SL: {sl:.4f}\n"
                                   f"📊 Volume: {current_volume:.0f}")
                            send_telegram_msg(CHAT_ID, msg)
                            
                        elif signal_type == "SELL" and trend_1d == "نزولی 🔴":
                            sl = current_price + (atr * 1.5)
                            tp = current_price - (atr * 3.0)
                            msg = (f"⚠️ <b>SELL SIGNAL: {coin}</b>\n\n"
                                   f"🌍 1D Trend: DOWN | ⏳ 4H Trend: DOWN\n"
                                   f"🕯️ Pattern: {pattern_name}\n"
                                   f"💰 Price: {current_price:.4f}\n"
                                   f"🎯 TP: {tp:.4f} | 🛑 SL: {sl:.4f}\n"
                                   f"📊 Volume: {current_volume:.0f}")
                            send_telegram_msg(CHAT_ID, msg)
        except Exception as e:
            pass
        time.sleep(0.3) 

if __name__ == "__main__":
    check_telegram_commands()
    scan_market()
