import requests
import time
import os
from datetime import datetime

# 🔐 خواندن توکن از Secrets گیت‌هاب
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

def calc_adx(highs, lows, closes, period=14):
    if len(closes) < period * 2: return 0
    tr_list, plus_dm, minus_dm = [], [], []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
    
    def smooth(data):
        smoothed = [sum(data[:period])]
        for i in range(period, len(data)):
            smoothed.append(smoothed[-1] - smoothed[-1]/period + data[i])
        return smoothed
    
    atr = smooth(tr_list)
    plus_di = [100 * p / a if a != 0 else 0 for p, a in zip(smooth(plus_dm), atr)]
    minus_di = [100 * m / a if a != 0 else 0 for m, a in zip(smooth(minus_dm), atr)]
    dx = [100 * abs(p - m) / (p + m) if (p + m) != 0 else 0 for p, m in zip(plus_di, minus_di)]
    adx_smooth = smooth(dx)
    return adx_smooth[-1] if adx_smooth else 0

# ================= تشخیص الگوهای کندل استیک =================
def check_candle_patterns(opens, closes, highs, lows):
    o1, c1 = opens[-2], closes[-2] 
    o2, c2 = opens[-1], closes[-1] 
    h2, l2 = highs[-1], lows[-1]
    
    body = abs(c2 - o2)
    upper_shadow = h2 - max(c2, o2)
    lower_shadow = min(c2, o2) - l2

    if c1 < o1 and c2 > o2 and c2 > o1 and o2 < c1:
        return "Bullish Engulfing"
    if lower_shadow > 2 * body and upper_shadow < 0.2 * body and c2 > o2:
        return "Hammer"
    if c1 > o1 and c2 < o2 and c2 < o1 and o2 > c1:
        return "Bearish Engulfing"
    if upper_shadow > 2 * body and lower_shadow < 0.2 * body and c2 < o2:
        return "Shooting Star"

    return None

# ================= حلقه اصلی اسکن =================
def scan_market():
    print(f"[{datetime.now()}] Scanning market...")
    for coin in WATCH_LIST:
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
                
                if len(closes) > 30:
                    current_price = closes[-1]
                    
                    ema9 = calc_ema(closes, 9)
                    ema20 = calc_ema(closes, 20)
                    rsi14 = calc_rsi(closes[-15:], 14)
                    macd_line = calc_macd(closes)
                    adx_val = calc_adx(highs, lows, closes, 14)
                    pattern = check_candle_patterns(opens, closes, highs, lows)
                    
                    if adx_val < 25:
                        continue
                        
                    if ema9 > ema20 and macd_line > 0 and 50 < rsi14 < 70 and pattern and ("Bullish" in pattern or "Hammer" in pattern):
                        tp = current_price * 1.04 
                        sl = current_price * 0.98 
                        msg = (f"🟢 <b>BUY SIGNAL</b>\n\n"
                               f"💰 Coin: <b>{coin}/USDT</b>\n"
                               f"📊 Price: {current_price:.4f}\n"
                               f"🕯️ Pattern: <b>{pattern}</b>\n"
                               f"📈 RSI: {rsi14:.2f} | ADX: {adx_val:.2f}\n"
                               f"🎯 Take Profit: {tp:.4f}\n"
                               f"🛑 Stop Loss: {sl:.4f}\n\n"
                               f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        send_telegram_msg(msg)
                        print(f"Buy signal sent for {coin}.")
                    
                    elif ema9 < ema20 and macd_line < 0 and rsi14 > 70 and pattern and ("Bearish" in pattern or "Shooting Star" in pattern):
                        tp = current_price * 0.96 
                        sl = current_price * 1.02 
                        msg = (f"🔴 <b>SELL SIGNAL</b>\n\n"
                               f"💰 Coin: <b>{coin}/USDT</b>\n"
                               f"📊 Price: {current_price:.4f}\n"
                               f"🕯️ Pattern: <b>{pattern}</b>\n"
                               f"📈 RSI: {rsi14:.2f} | ADX: {adx_val:.2f}\n"
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
