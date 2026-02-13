import requests
import pandas as pd
import time

BOT_TOKEN = "8332944943:AAGcS4fhzqU_OEnYjr1AF3gIltNoQma_1RA"
CHAT_ID = "1762390606"
API_KEY = "b86bc49f64ff406eb5a3b37d8898e861"

SYMBOL = "XAG/USD"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{8332944943:AAGcS4fhzqU_OEnYjr1AF3gIltNoQma_1RA}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

df = get_data()
if df is None:
    time.sleep(300)
    continue
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval=5min&outputsize=100&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        print("API ERROR:", data)
        return None

    df = pd.DataFrame(data["values"])
    df = df.astype(float)
    df = df.iloc[::-1]
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

last_signal = None

while True:
    try:
        df = get_data()

        df["ema9"] = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        df["rsi"] = compute_rsi(df["close"])

        bull_cross = df["ema9"].iloc[-2] < df["ema21"].iloc[-2] and df["ema9"].iloc[-1] > df["ema21"].iloc[-1]
        bear_cross = df["ema9"].iloc[-2] > df["ema21"].iloc[-2] and df["ema9"].iloc[-1] < df["ema21"].iloc[-1]

        rsi_bull = df["rsi"].iloc[-2] < 55 and df["rsi"].iloc[-1] > 55
        rsi_bear = df["rsi"].iloc[-2] > 45 and df["rsi"].iloc[-1] < 45

        if bull_cross and rsi_bull and last_signal != "LONG":
            send_telegram(f"🚀 SILVER LONG\nPrice: {df['close'].iloc[-1]}")
            last_signal = "LONG"

        elif bear_cross and rsi_bear and last_signal != "SHORT":
            send_telegram(f"🔻 SILVER SHORT\nPrice: {df['close'].iloc[-1]}")
            last_signal = "SHORT"

        time.sleep(300)

    except Exception as e:
        print("Error:", e)
        time.sleep(300)
