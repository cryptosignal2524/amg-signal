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

def calc_rsi(data, period=14):
    gains, losses = 0, 0
    for i in range(1, period+1):
        diff = data[i] - data[i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    avg_gain, avg_loss = gains / period, losses / period
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

def calc_stoch_rsi(data, rsi_period=14, stoch_period=14):
    if len(data) < rsi_period + stoch_period: return 50
    rsi_values = []
    for i in range(len(data) - rsi_period):
        rsi_values.append(calc_rsi(data[i:i+rsi_period+1], rsi_period))
    if len(rsi_values) < stoch_period: return 50
    recent_rsi = rsi_values[-stoch_period:]
    min_rsi, max_rsi = min(recent_rsi), max(recent_rsi)
    if max_rsi - min_rsi == 0: return 50
    return ((rsi_values[-1] - min_rsi) / (max_rsi - min_rsi)) * 100

def calc_bollinger(data, period=20, std_dev=2):
    if len(data) < period: return None, None, None, None
    sma = sum(data[-period:]) / period
    variance = sum((x - sma) ** 2 for x in data[-period:]) / period
    std = variance ** 0.5
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    bb_width = (upper_band - lower_band) / sma 
    return sma, upper_band, lower_band, bb_width

# ================= تحلیل اختصاصی (با نام ارز) =================
def analyze_coin(coin):
    try:
        url = f"https://api.kucoin.com/api/v1/market/candles?type=15min&symbol={coin}-USDT"
        response = requests.get(url, timeout=10).json()
        if response.get("code") == "200000":
            data = response.get("data", [])
            data.reverse()
            closes = [float(item[2]) for item in data]
            volumes = [float(item[5]) for item in data]
            
            if len(closes) > 50:
                current_price = closes[-1]
                current_volume = volumes[-1]
                
                stoch_rsi = calc_stoch_rsi(closes)
                sma, upper_band, lower_band, bb_width = calc_bollinger(closes, 20, 2)
                avg_volume = sum(volumes[-20:]) / 20
                
                status = "⚖️ خنثی (بدون سیگنال زودهنگام)"
                if stoch_rsi < 20:
                    status = "🟢 <b>آماده رشد (اشباع فروش StochRSI)</b>"
                elif stoch_rsi > 80:
                    status = "🔴 <b>آماده ریزش (اشباع خرید StochRSI)</b>"
                    
                msg = (f"📊 <b>تحلیل زودهنگام {coin}/USDT</b>\n\n"
                       f"💰 قیمت فعلی: {current_price:.4f}\n"
                       f"📈 وضعیت: {status}\n\n"
                       f"🔹 StochRSI: {stoch_rsi:.2f}\n"
                       f"🔹 فشردگی بولینگر: {bb_width:.4f}\n"
                       f"🔹 حجم فعلی: {current_volume:.0f} (میانگین: {avg_volume:.0f})\n\n"
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
                    # اگر دستور با /analyze شروع شده باشد
                    if text.startswith("/ANALYZE"):
                        parts = text.split()
                        if len(parts) > 1: coin = parts[1]
                    # اگر دستور با ANALYZE شروع شده باشد
                    elif text.startswith("ANALYZE"):
                        parts = text.split()
                        if len(parts) > 1: coin = parts[1]
                    # اگر فقط اسم ارز فرستاده شده باشد (مثل BTC)
                    elif len(text.split()) == 1 and text.isalnum():
                        coin = text
                    
                    if coin:
                        send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل زودهنگام {coin}...")
                        result = analyze_coin(coin)
                        send_telegram_msg(user_chat_id, result)
            
            if last_update_id:
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}", timeout=5)
    except Exception as e:
        print(f">>> Error: {e}")

# ================= حلقه اصلی (اسکن ۵۰ ارز برای سیگنال) =================
def scan_market():
    watch_list = get_top_50_coins()
    if not watch_list: watch_list = ["BTC", "ETH", "SOL", "XRP", "ADA"]
        
    print(f">>> Scanning {len(watch_list)} coins for Early Signals...")
    for coin in watch_list:
        try:
            url = f"https://api.kucoin.com/api/v1/market/candles?type=15min&symbol={coin}-USDT"
            response = requests.get(url, timeout=10).json()
            
            if response.get("code") == "200000":
                data = response.get("data", [])
                data.reverse()
                closes = [float(item[2]) for item in data]
                volumes = [float(item[5]) for item in data]
                
                if len(closes) > 50:
                    current_price = closes[-1]
                    current_volume = volumes[-1]
                    
                    stoch_rsi = calc_stoch_rsi(closes)
                    sma, upper_band, lower_band, bb_width = calc_bollinger(closes, 20, 2)
                    avg_volume = sum(volumes[-20:]) / 20
                    
                    # 🚀 سیگنال خرید زودهنگام
                    if stoch_rsi < 20 and bb_width < 0.05 and current_volume > (avg_volume * 1.5):
                        msg = (f"🚀 <b>EARLY WARNING: BUY {coin}</b>\n\n"
                               f"💰 Price: {current_price:.4f}\n"
                               f"📉 StochRSI: {stoch_rsi:.2f} (Oversold)\n"
                               f"📊 BB Squeeze: {bb_width:.4f} (Breakout Imminent)\n"
                               f"📈 Volume Spike: {current_volume:.0f} (Avg: {avg_volume:.0f})\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(CHAT_ID, msg)
                        print(f"Early Buy sent for {coin}.")
                    
                    # 🔻 سیگنال فروش زودهنگام
                    elif stoch_rsi > 80 and bb_width < 0.05 and current_volume > (avg_volume * 1.5):
                        msg = (f"🔻 <b>EARLY WARNING: SELL {coin}</b>\n\n"
                               f"💰 Price: {current_price:.4f}\n"
                               f"📈 StochRSI: {stoch_rsi:.2f} (Overbought)\n"
                               f"📊 BB Squeeze: {bb_width:.4f} (Breakdown Imminent)\n"
                               f"📉 Volume Spike: {current_volume:.0f} (Avg: {avg_volume:.0f})\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(CHAT_ID, msg)
                        print(f"Early Sell sent for {coin}.")
                    
        except Exception as e:
            pass
        time.sleep(0.3) 

if __name__ == "__main__":
    check_telegram_commands()
    scan_market()
