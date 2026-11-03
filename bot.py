import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = "9268038700:AAGEtH4cmpoQg7rzPs8h0APqB8-HO93ILz8"
CHAT_ID = "437930017" 
WATCH_LIST = ["BTC", "ETH", "XRP", "ADA", "SOL", "TON", "TRX", "DASH", "DOGE", "AVAX", "LINK", "MATIC", "LTC", "BCH", "UNI", "XLM", "SHIB", "DOT", "ATOM", "NEAR"]

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

def calculate_indicators(closes):
    def ema(data, period):
        k = 2 / (period + 1)
        ema_val = data[0]
        for price in data[1:]:
            ema_val = price * k + ema_val * (1 - k)
        return ema_val
    def rsi(data, period=14):
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
    return ema(closes, 9), ema(closes, 20), rsi(closes[-15:], 14)

def scan_market():
    print(f"[{datetime.now()}] Scanning market...")
    for coin in WATCH_LIST:
        try:
            url = f"https://api.kucoin.com/api/v1/market/candles?type=4hour&symbol={coin}-USDT"
            response = requests.get(url, timeout=10).json()
            if response.get("code") == "200000":
                data = response.get("data", [])
                data.reverse()
                closes = [float(item[2]) for item in data]
                if len(closes) > 20:
                    ema9, ema20, rsi14 = calculate_indicators(closes)
                    if ema9 > ema20 and 50 < rsi14 < 70:
                        send_telegram_msg(f"🟢 <b>BUY SIGNAL</b>\n\n💰 Coin: <b>{coin}/USDT</b>\n📊 Price: {closes[-1]}\n📈 RSI: {rsi14:.2f}")
                    elif ema9 < ema20 and rsi14 > 70:
                        send_telegram_msg(f"🔴 <b>SELL SIGNAL</b>\n\n💰 Coin: <b>{coin}/USDT</b>\n📊 Price: {closes[-1]}\n📈 RSI: {rsi14:.2f}")
        except Exception as e:
            print(f"Error {coin}: {e}")
        time.sleep(1)

if __name__ == "__main__":
    scan_market()
