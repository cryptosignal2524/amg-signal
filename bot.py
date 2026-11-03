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

# ================= تشخیص الگوهای کندلی و چارتی =================
def detect_patterns(opens, highs, lows, closes, volumes):
    if len(closes) < 20: return None, None
    
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    prev_o, prev_c = opens[-2], closes[-2]
    
    body = abs(c - o)
    upper_shadow = h - max(c, o)
    lower_shadow = min(c, o) - l
    avg_volume = sum(volumes[-20:]) / 20
    
    # 1. کندل مارابوزو (Marubozu) - قدرت خرید یا فروش خالص
    if body > (h - l) * 0.9:
        if c > o: return "Bullish Marubozu (مارابوزوی صعودی)", "BUY"
        else: return "Bearish Marubozu (مارابوزوی نزولی)", "SELL"

    # 2. چکش (Hammer)
    if lower_shadow > 2 * body and upper_shadow < 0.2 * body and c > o:
        return "Hammer (چکش)", "BUY"
        
    # 3. ستاره دنباله‌دار (Shooting Star)
    if upper_shadow > 2 * body and lower_shadow < 0.2 * body and c < o:
        return "Shooting Star (ستاره دنباله‌دار)", "SELL"

    # 4. پوشای صعودی (Bullish Engulfing)
    if prev_c < prev_o and c > o and c > prev_o and o < prev_c:
        return "Bullish Engulfing (پوشای صعودی)", "BUY"
        
    # 5. پوشای نزولی (Bearish Engulfing)
    if prev_c > prev_o and c < o and c < prev_o and o > prev_c:
        return "Bearish Engulfing (پوشای نزولی)", "SELL"

    # 6. الگوی پرچم صعودی ساده شده (Bullish Flag)
    # یک رشد شارپ در 5 کندل اخیر و سپس یک استراحت کوچک
    recent_5_closes = closes[-5:]
    if recent_5_closes[0] < recent_5_closes[-1] * 0.98 and c < recent_5_closes[-2] and (h - l) < (h - l) * 0.5:
         if avg_volume > avg_volume * 0.8: # حجم در حال خشک شدن (استراحت)
             return "Possible Bullish Flag (پرچم صعودی)", "BUY"

    # 7. کف دوقلو (Double Bottom) در 15 کندل اخیر
    last_15_lows = lows[-15:]
    min_low = min(last_15_lows)
    if l - min_low < min_low * 0.01 and c > o: # کندل فعلی نزدیک کف قبلی است و صعودی بسته شده
        return "Potential Double Bottom (کف دوقلو)", "BUY"

    return None, None

# ================= تحلیل اختصاصی =================
def analyze_coin(coin):
    try:
        # تایم‌فریم ۱ ساعته برای کندل‌شناسی بهتر
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
                
                ema50 = calc_ema(closes, 50)
                atr = calc_atr(highs, lows, closes)
                
                pattern_name, signal_type = detect_patterns(opens, highs, lows, closes, volumes)
                
                position = "⚪ خنثی (Neutral)"
                tp_sl_info = ""
                
                # فیلتر روند اصلی: بالای EMA50 (فقط خرید) - زیر EMA50 (فقط فروش)
                if signal_type == "BUY" and current_price > ema50:
                    if current_volume > avg_volume * 1.2: # تایید حجم
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

                msg = (f"📊 <b>تحلیل حرفه‌ای {coin}/USDT</b>\n"
                       f"━━━━━━━━━━━━━━━\n"
                       f"🎯 <b>موقعیت: {position}</b>\n\n"
                       f"💰 قیمت فعلی: {current_price:.4f}\n"
                       f"🕯️ الگوی شناسایی شده: {pattern_name if pattern_name else 'الگوی خاصی یافت نشد'}\n"
                       f"📈 روند اصلی (EMA50): {'صعودی ✅' if current_price > ema50 else 'نزولی ❌'}\n"
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
                        send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل {coin}...")
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
        
    print(f">>> Scanning {len(watch_list)} coins...")
    for coin in watch_list:
        try:
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
                    ema50 = calc_ema(closes, 50)
                    atr = calc_atr(highs, lows, closes)
                    
                    pattern_name, signal_type = detect_patterns(opens, highs, lows, closes, volumes)
                    
                    if pattern_name and current_volume > avg_volume * 1.2:
                        if signal_type == "BUY" and current_price > ema50:
                            sl = current_price - (atr * 1.5)
                            tp = current_price + (atr * 3.0)
                            msg = (f"🚀 <b>BUY SIGNAL: {coin}</b>\n\n"
                                   f"🕯️ Pattern: {pattern_name}\n"
                                   f"💰 Price: {current_price:.4f}\n"
                                   f"🎯 TP: {tp:.4f} | 🛑 SL: {sl:.4f}\n"
                                   f"📊 Volume: {current_volume:.0f}")
                            send_telegram_msg(CHAT_ID, msg)
                            print(f"Buy sent for {coin}.")
                            
                        elif signal_type == "SELL" and current_price < ema50:
                            sl = current_price + (atr * 1.5)
                            tp = current_price - (atr * 3.0)
                            msg = (f"⚠️ <b>SELL SIGNAL: {coin}</b>\n\n"
                                   f"🕯️ Pattern: {pattern_name}\n"
                                   f"💰 Price: {current_price:.4f}\n"
                                   f"🎯 TP: {tp:.4f} | 🛑 SL: {sl:.4f}\n"
                                   f"📊 Volume: {current_volume:.0f}")
                            send_telegram_msg(CHAT_ID, msg)
                            print(f"Sell sent for {coin}.")
        except Exception as e:
            pass
        time.sleep(0.5) 

if __name__ == "__main__":
    check_telegram_commands()
    scan_market()
