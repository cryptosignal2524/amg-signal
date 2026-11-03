import requests
import time
import os
from datetime import datetime

# 🔐 خواندن توکن از Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID") # کانال اصلی

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
            # فیلتر جفت‌ارزهای USDT
            usdt_pairs = [t for t in tickers if t["symbol"].endswith("-USDT")]
            # مرتب‌سازی بر اساس حجم معاملات ۲۴ ساعته (نزولی)
            usdt_pairs.sort(key=lambda x: float(x["volValue"]), reverse=True)
            # برداشتن ۵۰ ارز اول
            top_50 = [t["symbol"].replace("-USDT", "") for t in usdt_pairs[:50]]
            return top_50
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
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_macd(data):
    return calc_ema(data, 12) - calc_ema(data, 26)

def calc_bollinger(data, period=20, std_dev=2):
    if len(data) < period: return None, None, None
    sma = sum(data[-period:]) / period
    variance = sum((x - sma) ** 2 for x in data[-period:]) / period
    std = variance ** 0.5
    return sma, sma + (std * std_dev), sma - (std * std_dev)

# ================= تحلیل یک ارز خاص (دستی) =================
def analyze_coin(coin):
    try:
        url = f"https://api.kucoin.com/api/v1/market/candles?type=15min&symbol={coin}-USDT"
        response = requests.get(url, timeout=10).json()
        if response.get("code") == "200000":
            data = response.get("data", [])
            data.reverse()
            closes = [float(item[2]) for item in data]
            volumes = [float(item[5]) for item in data]
            
            if len(closes) > 30:
                current_price = closes[-1]
                ema9 = calc_ema(closes, 9)
                ema20 = calc_ema(closes, 20)
                rsi14 = calc_rsi(closes[-15:], 14)
                macd_line = calc_macd(closes)
                sma, upper_band, lower_band = calc_bollinger(closes, 20, 2)
                avg_volume = sum(volumes[-20:]) / 20
                
                status = "⚖️ خنثی (بدون سیگنال قوی)"
                if ema9 > ema20 and macd_line > 0 and 50 < rsi14 < 75 and current_price > upper_band:
                    status = "🟢 <b>سیگنال خرید (صعودی)</b>"
                elif ema9 < ema20 and macd_line < 0 and 25 < rsi14 < 50 and current_price < lower_band:
                    status = "🔴 <b>سیگنال فروش (نزولی)</b>"
                    
                msg = (f"📊 <b>تحلیل اختصاصی {coin}/USDT</b>\n\n"
                       f"💰 قیمت فعلی: {current_price:.4f}\n"
                       f"📈 وضعیت: {status}\n\n"
                       f"🔹 RSI: {rsi14:.2f}\n"
                       f"🔹 MACD: {'مثبت' if macd_line > 0 else 'منفی'}\n"
                       f"🔹 EMA9 > EMA20: {'بله' if ema9 > ema20 else 'خیر'}\n"
                       f"🔹 حجم معاملات: {current_volume:.0f} (میانگین: {avg_volume:.0f})\n\n"
                       f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                return msg
    except Exception as e:
        return f"❌ خطا در تحلیل {coin}: {e}"
    return f"❌ داده کافی برای {coin} یافت نشد."

# ================= چک کردن پیام‌های کاربران =================
def check_telegram_commands():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        response = requests.get(url, timeout=10).json()
        
        if response.get("ok") and response.get("result"):
            now = time.time()
            for msg in response["result"]:
                # بررسی پیام‌های ۵ دقیقه اخیر
                if "message" in msg and "text" in msg["message"]:
                    msg_date = msg["message"].get("date", 0)
                    if now - msg_date < 300: 
                        text = msg["message"]["text"]
                        user_chat_id = msg["message"]["chat"]["id"]
                        
                        if text.startswith("/analyze"):
                            parts = text.split()
                            if len(parts) > 1:
                                coin = parts[1].upper()
                                send_telegram_msg(user_chat_id, f"⏳ در حال تحلیل {coin}... لطفا صبر کنید.")
                                result = analyze_coin(coin)
                                send_telegram_msg(user_chat_id, result)
                            else:
                                send_telegram_msg(user_chat_id, "⚠️ لطفاً نام ارز را وارد کنید. مثال:\n<code>/analyze BTC</code>")
    except Exception as e:
        print(f"Error checking commands: {e}")

# ================= حلقه اصلی =================
def scan_market():
    print(f"[{datetime.now()}] Fetching Top 50 Coins...")
    watch_list = get_top_50_coins()
    
    if not watch_list:
        print("Could not fetch top coins. Using fallback list.")
        watch_list = ["BTC", "ETH", "SOL", "XRP", "ADA"]
        
    print(f"Scanning {len(watch_list)} coins...")
    for coin in watch_list:
        try:
            url = f"https://api.kucoin.com/api/v1/market/candles?type=15min&symbol={coin}-USDT"
            response = requests.get(url, timeout=10).json()
            
            if response.get("code") == "200000":
                data = response.get("data", [])
                data.reverse()
                closes = [float(item[2]) for item in data]
                volumes = [float(item[5]) for item in data]
                
                if len(closes) > 30:
                    current_price = closes[-1]
                    current_volume = volumes[-1]
                    ema9 = calc_ema(closes, 9)
                    ema20 = calc_ema(closes, 20)
                    rsi14 = calc_rsi(closes[-15:], 14)
                    macd_line = calc_macd(closes)
                    sma, upper_band, lower_band = calc_bollinger(closes, 20, 2)
                    avg_volume = sum(volumes[-20:]) / 20 
                    
                    # سیگنال خرید
                    if ema9 > ema20 and macd_line > 0 and 50 < rsi14 < 75:
                        if current_price > upper_band and current_volume > (avg_volume * 1.5):
                            tp = current_price * 1.02 
                            sl = current_price * 0.99 
                            msg = (f"🚀 <b>EARLY BUY SIGNAL</b>\n\n"
                                   f"💰 Coin: <b>{coin}/USDT</b>\n"
                                   f"📊 Price: {current_price:.4f}\n"
                                   f"📈 RSI: {rsi14:.2f}\n"
                                   f"🎯 Take Profit: {tp:.4f}\n"
                                   f"🛑 Stop Loss: {sl:.4f}")
                            send_telegram_msg(CHAT_ID, msg)
                            print(f"Buy signal sent for {coin}.")
                    
                    # سیگنال فروش
                    elif ema9 < ema20 and macd_line < 0 and 25 < rsi14 < 50:
                        if current_price < lower_band and current_volume > (avg_volume * 1.5):
                            tp = current_price * 0.98 
                            sl = current_price * 1.01 
                            msg = (f"⚠️ <b>EARLY SELL SIGNAL</b>\n\n"
                                   f"💰 Coin: <b>{coin}/USDT</b>\n"
                                   f"📊 Price: {current_price:.4f}\n"
                                   f"📈 RSI: {rsi14:.2f}\n"
                                   f"🎯 Take Profit: {tp:.4f}\n"
                                   f"🛑 Stop Loss: {sl:.4f}")
                            send_telegram_msg(CHAT_ID, msg)
                            print(f"Sell signal sent for {coin}.")
                    
        except Exception as e:
            print(f"Error {coin}: {e}")
        time.sleep(0.5) 

if __name__ == "__main__":
    check_telegram_commands()
    scan_market()
