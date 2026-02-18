import requests
import pandas as pd
import time
import os

# Load Railway environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(url, data=payload)
    print("Telegram response:", response.text)

def get_data():
    url = "https://stooq.com/q/d/l/?s=xagusd&i=5"
    response = requests.get(url)

    if response.status_code != 200:
        print("Data fetch failed")
        return None

    from io import StringIO
    df = pd.read_csv(StringIO(response.text))

    if df.empty:
        print("Empty dataframe")
        return None

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close"
    })

    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


print("Bot is running...")

# Startup test message
send_telegram("Silver bot is now online")

last_signal = None

while True:
    try:
        df = get_data()

        if df is None or len(df) < 30:
            time.sleep(300)
            continue

        df["ema9"] = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        df["rsi"] = compute_rsi(df["close"])

        trend_long = (
            df["ema9"].iloc[-1] > df["ema21"].iloc[-1] and
            df["rsi"].iloc[-2] < 50 and
            df["rsi"].iloc[-1] > 50
        )

        trend_short = (
            df["ema9"].iloc[-1] < df["ema21"].iloc[-1] and
            df["rsi"].iloc[-2] > 50 and
            df["rsi"].iloc[-1] < 50
        )

        signal = None

        if trend_long:
            signal = "TREND LONG"
        elif trend_short:
            signal = "TREND SHORT"

        if signal and signal != last_signal:
            price = df["close"].iloc[-1]
            send_telegram(f"{signal}\nPrice: {price}")
            last_signal = signal

        time.sleep(300)

    except Exception as e:
        print("Runtime Error:", e)
        time.sleep(300)
