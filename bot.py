import requests
import time
import os
from datetime import datetime
import statistics

# 🔐 خواندن توکن از Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

WATCH_LIST = ["BTC", "ETH", "XRP", "ADA", "SOL", "TON", "TRX", "DASH", "DOGE", "AVAX", "LINK", "MATIC", "LTC", "BCH", "UNI", "XLM", "SHIB", "DOT", "ATOM", "NEAR"]

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

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

# باند بولینگر
def calc_bollinger(data, period=20, std_dev=2):
    if len(data) < period: return None, None, None
    sma = sum(data[-period:]) / period
    variance = sum((x - sma) ** 2 for x in data[-period:]) / period
    std = variance ** 0.5
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return sma, upper_band, lower_band

# ================= حلقه اصلی اسکن =================
def scan_market():
    print(f"[{datetime.now()}] Scanning market (15m)...")
    for coin in WATCH_LIST:
        try:
            # تغییر به کندل ۱۵ دقیقه‌ای
            url = f"https://api.kucoin.com/api/v1/market/candles?type=15min&symbol={coin}-USDT"
            response = requests.get(url, timeout=10).json()
            
            if response.get("code") == "200000":
                data = response.get("data", [])
                data.reverse()
                
                closes = [float(item[2]) for item in data]
                volumes = [float(item[5]) for item in data] # ایندکس 5 حجم است
                
                if len(closes) > 30:
                    current_price = closes[-1]
                    current_volume = volumes[-1]
                    
                    # محاسبات
                    ema9 = calc_ema(closes, 9)
                    ema20 = calc_ema(closes, 20)
                    rsi14 = calc_rsi(closes[-15:], 14)
                    macd_line = calc_macd(closes)
                    
                    # بولینگر
                    sma, upper_band, lower_band = calc_bollinger(closes, 20, 2)
                    
                    # میانگین حجم ۲۰ کندل اخیر (برای تشخیص حجم غیرعادی)
                    avg_volume = sum(volumes[-20:]) / 20 
                    
                    # 🔥 منطق سیگنال خرید (زودتر و دقیق‌تر) 🔥
                    # 1. قیمت از باند بالایی بولینگر عبور کنه (شروع حرکت صعودی)
                    # 2. حجم معاملات حداقل 1.5 برابر میانگین باشه (تاییدیه قدرت خرید)
                    # 3. میانگین‌ها صعودی باشن و RSI در محدوده امن
                    if ema9 > ema20 and macd_line > 0 and 50 < rsi14 < 75:
                        if current_price > upper_band and current_volume > (avg_volume * 1.5):
                            tp = current_price * 1.02 # حد سود 2%
                            sl = current_price * 0.99 # حد ضرر 1%
                            msg = (f"🚀 <b>EARLY BUY SIGNAL</b>\n\n"
                                   f"💰 Coin: <b>{coin}/USDT</b>\n"
                                   f"📊 Price: {current_price:.4f}\n"
                                   f"📈 RSI: {rsi14:.2f}\n"
                                   f"📊 Volume Spike: {current_volume:.2f} (Avg: {avg_volume:.2f})\n"
                                   f"🎯 Take Profit: {tp:.4f}\n"
                                   f"🛑 Stop Loss: {sl:.4f}\n\n"
                                   f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                            send_telegram_msg(msg)
                            print(f"Buy signal sent for {coin}.")
                    
                    # 🔥 منطق سیگنال فروش (زودتر و دقیق‌تر) 🔥
                    elif ema9 < ema20 and macd_line < 0 and 25 < rsi14 < 50:
                        if current_price < lower_band and current_volume > (avg_volume * 1.5):
                            tp = current_price * 0.98 
                            sl = current_price * 1.01 
                            msg = (f"⚠️ <b>EARLY SELL SIGNAL</b>\n\n"
                                   f"💰 Coin: <b>{coin}/USDT</b>\n"
                                   f"📊 Price: {current_price:.4f}\n"
                                   f"📈 RSI: {rsi14:.2f}\n"
                                   f"📊 Volume Spike: {current_volume:.2f} (Avg: {avg_volume:.2f})\n"
                                   f"🎯 Take Profit: {tp:.4f}\n"
                                   f"🛑 Stop Loss: {sl:.4f}\n\n"
                                   f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                            send_telegram_msg(msg)
                            print(f"Sell signal sent for {coin}.")
                    
        except Exception as e:
            print(f"Error {coin}: {e}")
        time.sleep(1)

if __name__ == "__main__":
    scan_market()
