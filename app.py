import requests
import pandas as pd
import time
from io import StringIO

# =============================
# CONFIG
# =============================

BOT_TOKEN = "8332944943:AAGcS4fhzqU_OEnYjr1AF3gIltNoQma_1RA"
CHAT_ID = "1762390606"

CHECK_INTERVAL = 300  # 5 minutes


# =============================
# TELEGRAM
# =============================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)


# =============================
# DATA SOURCE (STOOQ)
# =============================

def get_data():
    url = "https://stooq.com/q/d/l/?s=xagusd&i=5"
    response = requests.get(url)

    if response.status_code != 200:
        print("API ERROR:", response.text)
        return None

    df = pd.read_csv(StringIO(response.text))

    if df.empty or len(df) < 30:
        return None

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close"
    })

    df = df.dropna()
    return df


# =============================
# RSI
# =============================

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =============================
# MAIN LOOP
# =============================

last_signal = None

while True:
    try:
        df = get_data()

        if df is None:
            time.sleep(CHECK_INTERVAL)
            continue

        # Indicators
        df["ema9"] = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        df["rsi"] = compute_rsi(df["close"])

        # =============================
        # REVERSAL ENGINE
        # =============================

        reversal_long = (
            df["rsi"].iloc[-5:-1].min() < 30 and
            df["rsi"].iloc[-2] < 45 and df["rsi"].iloc[-1] > 45 and
            df["close"].iloc[-1] > df["high"].iloc[-4:-1].max() and
            df["ema9"].iloc[-1] > df["ema9"].iloc[-2]
        )

        reversal_short = (
            df["rsi"].iloc[-5:-1].max() > 70 and
            df["rsi"].iloc[-2] > 55 and df["rsi"].iloc[-1] < 55 and
            df["close"].iloc[-1] < df["low"].iloc[-4:-1].min() and
            df["ema9"].iloc[-1] < df["ema9"].iloc[-2]
        )

        # =============================
        # TREND ENGINE
        # =============================

        trend_long = (
            df["ema9"].iloc[-1] > df["ema21"].iloc[-1] and
            df["rsi"].iloc[-2] < 50 and df["rsi"].iloc[-1] > 50 and
            df["close"].iloc[-1] > df["high"].iloc[-2]
        )

        trend_short = (
            df["ema9"].iloc[-1] < df["ema21"].iloc[-1] and
            df["rsi"].iloc[-2] > 50 and df["rsi"].iloc[-1] < 50 and
            df["close"].iloc[-1] < df["low"].iloc[-2]
        )

        # =============================
        # SIGNAL DECISION
        # =============================

        signal = None

        if reversal_long:
            signal = "🟢 REVERSAL LONG"

        elif reversal_short:
            signal = "🔴 REVERSAL SHORT"

        elif trend_long:
            signal = "🔵 TREND LONG"

        elif trend_short:
            signal = "🟠 TREND SHORT"

        # =============================
        # SEND ALERT
        # =============================

        if signal and last_signal != signal:
            price = df["close"].iloc[-1]
            send_telegram(f"{signal}\nPrice: {price}")
            last_signal = signal
            print("Signal sent:", signal)

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        print("Runtime Error:", e)
        time.sleep(CHECK_INTERVAL)
