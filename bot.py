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
    avg_volume = sum(volumes[-20:]) / 20
    
    # کندل مارابوزو
    if body > (h - l) * 0.9:
        if c > o: return "Bullish Marubozu", "BUY"
        else: return "Bearish Marubozu", "SELL"
    # چکش
    if lower_shadow > 2 * body and upper_shadow < 0.2 * body and c > o:
        return "Hammer", "BUY"
    # ستاره دنباله‌دار
    if upper_shadow > 2 * body and lower_shadow < 0.2 * body and c < o:
        return "Shooting Star", "SELL"
    # پوشای صعودی
    if prev_c < prev_o and c > o and c > prev_o and o < prev_c:
        return "Bullish Engulfing", "BUY"
    # پوشای نزولی
    if prev_c > prev_o and c < o and c < prev_o and o > prev_c:
        return "Bearish Engulfing", "SELL"
    return None, None

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

# ================= تحلیل اختصاصی (سه‌گانه) =================
def analyze_coin(coin):
    try:
        # ۱. چک کردن روند روزانه
        trend_1d, price_1d, _ = get_trend(coin, "1day")
        time.sleep(0.2)
        # ۲. چک کردن روند ۴ ساعته
        trend_4h, price_4h, _ = get_trend(coin, "4hour")
        time.sleep(0.2)
        
        # ۳. دریافت کندل‌های ۱ ساعته برای پیدا کردن الگو
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
                
                position = "⚪ خنثی (منتظر هم‌جهت شدن تایم‌فریم‌ها)"
                tp_sl_info = ""
                
                # 🚀 شرط خرید سه‌گانه (روند روزانه و ۴ ساعته صعودی + الگوی خرید در ۱ ساعته)
                if trend_1d == "صعودی 🟢" and trend_4h == "صعودی 🟢":
                    if signal_type == "BUY" and current_volume > avg_volume * 1.2:
                        position = "🟢 <b>سیگنال خرید قوی (BUY)</b>"
                        sl = current_price - (atr * 1.5)
                        tp = current_price + (atr * 3.0)
                        tp_sl_info = f"\n🎯 <b>Take Profit:</b> {tp:.4f}\n🛑 <b>Stop Loss:</b> {sl:.4f}"
                
                # 🔻 شرط فروش سه‌گانه (روند روزانه و ۴ ساعته نزولی + الگوی فروش در ۱ ساعته)
                elif trend_1d == "نزولی 🔴" and trend_4h == "نزولی 🔴":
                    if signal_type == "SELL" and current_volume > avg_volume * 1.2:
                        position = "🔴 <b>سیگنال فروش قوی (SELL)</b>"
                        sl = current_price + (atr * 1.5)
                        tp = current_price - (atr * 3.0)
                        tp_sl_info = f"\n🎯 <b>Take Profit:</b> {tp:.4f}\n🛑 <b>Stop Loss:</b> {sl:.4f}"

                msg = (f"📊 <b>تحلیل چند تایم‌فریمی {coin}/USDT</b>\n"
                       f"━━━━━━━━━━━━━━━\n"
                       f"🎯 <b>موقعیت: {position}</b>\n\n"
                       f"🌍 روند روزانه (1D): {trend_1d}\n"
                       f"⏳ روند ۴ ساعته (4H): {trend_4h}\n"
                       f"🕯️ الگوی ۱ ساعته (1H): {pattern_name if pattern_name else 'بدون الگو'}\n\n"
                       f"💰 قیمت فعلی: {current_price:.4f}\n"
                       f"📊 حجم: {current_volume:.0f} (میانگین: {avg_volume:.0f}){tp_sl_info}\n\n"
                       f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                return msg
    except Exception as e:
        return f"❌ خطا در تحلیل {coin}: {e}"
    return f"❌ ارز {coin} در صرافی یافت نشد یا داده کافی ندارد."

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
                    if text == "/START": continue
                    
                    coin = None
                    if text.startswith("/ANALYZE") or text.startswith("ANALYZE"):
                        parts = text.split()
                        if len(parts) > 1: coin = parts[1]
                    elif len(text.split()) == 1 and text.isalnum():
                        coin = text
                    
                    if coin:
                        send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل سه‌گانه {coin}...")
                        result = analyze_coin(coin)
                        send_telegram_msg(user_chat_id, result)
            if last_update_id:
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}", timeout=5)
    except Exception as e:
        print(f">>> Error: {e}")

# ================= حلقه اصلی (اسکن ۵۰ ارز) =================
def scan_market():
    watch_list = get_top_50_coins()
    if not watch_list: watch_list = ["BTC", "ETH", "SOL", "XRP", "ADA"]
        
    print(f">>> Scanning {len(watch_list)} coins with Multi-Timeframe...")
    for coin in watch_list:
        try:
            trend_1d, _, _ = get_trend(coin, "1day")
            time.sleep(0.1)
            trend_4h, _, _ = get_trend(coin, "4hour")
            time.sleep(0.1)
            
            # اگر روند روزانه و ۴ ساعته هم‌جهت نبودن، ادامه بده (وقت رو تلف نکن)
            if "نامشخص" in trend_1d or "نامشخص" in trend_4h:
                continue
            if trend_1d != trend_4h:
                continue

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
                            print(f"Buy sent for {coin}.")
                            
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
                            print(f"Sell sent for {coin}.")
        except Exception as e:
            pass
        time.sleep(0.3) 

if __name__ == "__main__":
    check_telegram_commands()
    scan_market()
