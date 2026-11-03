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

def calc_ema(data, period):
    k = 2 / (period + 1)
    ema_val = data[0]
    for price in data[1:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val

def calc_smf(highs, lows, closes, period=14, smooth_period=3):
    """محاسبه SMF با هموارسازی برای دقت بالاتر"""
    if len(closes) < period + smooth_period: return 50
    
    raw_k_values = []
    for i in range(smooth_period):
        idx = len(closes) - smooth_period + i
        current_closes = closes[:idx+1]
        recent_highs = highs[idx-period+1:idx+1]
        recent_lows = lows[idx-period+1:idx+1]
        
        highest_high = max(recent_highs)
        lowest_low = min(recent_lows)
        
        if highest_high - lowest_low == 0:
            raw_k_values.append(50)
        else:
            raw_k = ((current_closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
            raw_k_values.append(raw_k)
            
    # هموارسازی با میانگین متحرک
    return sum(raw_k_values) / len(raw_k_values)

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
        volumes = [float(item[5]) for item in data]
        
        if len(closes) > 50:
            current_price = closes[-1]
            current_open = opens[-1]
            current_volume = volumes[-1]
            avg_volume = sum(volumes[-20:]) / 20
            ema50 = calc_ema(closes, 50)
            smf = calc_smf(highs, lows, closes, 14, 3)
            
            position = "⚪ خنثی"
            reason = "شرایط ایده‌آل فراهم نیست"
            
            # 🟢 شرایط خرید دقیق
            # 1. SMF زیر 20 (اشباع فروش)
            # 2. روند صعودی (بالای EMA50)
            # 3. حجم 1.2 برابر میانگین
            # 4. کندل سبز
            if smf < 20:
                if current_price > ema50 and current_volume > (avg_volume * 1.2) and current_price > current_open:
                    position = "🟢 <b>سیگنال خرید قوی (BUY)</b>"
                    reason = "SMF اشباع فروش + تایید روند و حجم"
                else:
                    position = "🟡 نزدیک به خرید (منتظر تاییدیه)"
                    reason = "SMF پایین است اما روند/حجم/کندل تایید نکرد"
            
            # 🔴 شرایط فروش دقیق
            # 1. SMF بالای 80 (اشباع خرید)
            # 2. روند نزولی (زیر EMA50)
            # 3. حجم 1.2 برابر میانگین
            # 4. کندل قرمز
            elif smf > 80:
                if current_price < ema50 and current_volume > (avg_volume * 1.2) and current_price < current_open:
                    position = "🔴 <b>سیگنال فروش قوی (SELL)</b>"
                    reason = "SMF اشباع خرید + تایید روند و حجم"
                else:
                    position = "🟠 نزدیک به فروش (منتظر تاییدیه)"
                    reason = "SMF بالا است اما روند/حجم/کندل تایید نکرد"

            msg = (f"📊 <b>تحلیل دقیق SMF {coin}/USDT (تایم‌فریم {tf})</b>\n"
                   f"━━━━━━━━━━━━━━━\n"
                   f"🎯 <b>موقعیت: {position}</b>\n"
                   f"💡 دلیل: {reason}\n\n"
                   f"💰 قیمت فعلی: {current_price:.4f}\n"
                   f"📊 مقدار SMF: {smf:.2f}\n"
                   f"📈 روند (EMA50): {'صعودی ✅' if current_price > ema50 else 'نزولی ❌'}\n"
                   f"📊 حجم: {current_volume:.0f} (میانگین: {avg_volume:.0f})\n\n"
                   f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            return msg
        else:
            return f"❌ داده کافی برای تحلیل {coin} وجود ندارد."
    except Exception as e:
        return f"❌ خطا: {e}"

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
                        send_telegram_msg(user_chat_id, "👋 سلام!\nاسم ارز رو بفرست تا با سیستم دقیق SMF تحلیل ۵ دقیقه‌ای بگیرم (مثلا: BTC).")
                        continue
                    
                    parts = text.split()
                    if len(parts) == 1 and text.isalnum() and len(text) <= 6:
                        send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل دقیق SMF {text} (تایم‌فریم 5m)...")
                        result = analyze_coin(text, "5min")
                        send_telegram_msg(user_chat_id, result)
                    
                    elif len(parts) == 2:
                        coin = parts[0]
                        tf_input = parts[1].lower()
                        tf_map = {"15m": "15min", "1h": "1hour", "4h": "4hour", "1d": "1day"}
                        tf = tf_map.get(tf_input)
                        if tf:
                            send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل دقیق SMF {coin} در تایم‌فریم {tf}...")
                            result = analyze_coin(coin, tf)
                            send_telegram_msg(user_chat_id, result)
                        else:
                            send_telegram_msg(user_chat_id, "❌ تایم‌فریم نامعتبر است. از 15m، 1h، 4h یا 1d استفاده کنید.")
            
            if last_update_id:
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}", timeout=5)
    except Exception as e:
        print(f">>> Error: {e}")

def scan_market():
    watch_list = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "LTC", "LINK", "MATIC"]
    print(f">>> Scanning {len(watch_list)} coins for High-Accuracy SMF signals...")
    for coin in watch_list:
        try:
            url = f"https://api.kucoin.com/api/v1/market/candles?type=5min&symbol={coin}-USDT"
            response = requests.get(url, timeout=10).json()
            if response.get("code") == "200000":
                data = response.get("data", [])
                data.reverse()
                opens = [float(item[1]) for item in data]
                highs = [float(item[3]) for item in data]
                lows = [float(item[4]) for item in data]
                closes = [float(item[2]) for item in data]
                volumes = [float(item[5]) for item in data]
                
                if len(closes) > 50:
                    smf = calc_smf(highs, lows, closes, 14, 3)
                    current_price = closes[-1]
                    current_open = opens[-1]
                    current_volume = volumes[-1]
                    avg_volume = sum(volumes[-20:]) / 20
                    ema50 = calc_ema(closes, 50)
                    
                    # 🚀 فقط سیگنال‌های فوق‌العاده دقیق به کانال برن
                    if smf < 20 and current_price > ema50 and current_volume > (avg_volume * 1.2) and current_price > current_open:
                        msg = (f"🚀 <b>HIGH-ACCURACY SMF BUY: {coin}</b>\n\n"
                               f"💰 Price: {current_price:.4f}\n"
                               f"📊 SMF: {smf:.2f} (Oversold)\n"
                               f"📈 Trend: UP | 📊 Volume: {current_volume:.0f}\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(CHAT_ID, msg)
                    elif smf > 80 and current_price < ema50 and current_volume > (avg_volume * 1.2) and current_price < current_open:
                        msg = (f"⚠️ <b>HIGH-ACCURACY SMF SELL: {coin}</b>\n\n"
                               f"💰 Price: {current_price:.4f}\n"
                               f"📊 SMF: {smf:.2f} (Overbought)\n"
                               f"📉 Trend: DOWN | 📊 Volume: {current_volume:.0f}\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(CHAT_ID, msg)
        except Exception as e:
            pass
        time.sleep(0.3)

if __name__ == "__main__":
    check_telegram_commands()
    scan_market()
