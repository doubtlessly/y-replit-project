import os
import requests
import pandas as pd
import numpy as np
import ccxt
import ta
from datetime import datetime
from dotenv import load_dotenv
import time

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === [1] Telegram Alert ===
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        res = requests.post(url, data=payload)
        print("📨 Telegram response:", res.status_code, res.text, flush=True)
    except Exception as e:
        print(f"❌ Telegram send error: {e}", flush=True)

# === [2] Market Data ===
def fetch_market_data(symbol, exchange):
    try:
        bars = exchange.fetch_ohlcv(f"{symbol}/USDT", timeframe='15m', limit=150)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"⚠️ Failed to fetch market data for {symbol}: {e}", flush=True)
        return None

# === [3] Analyzer ===
def analyze_coin(symbol, df):
    try:
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']

        ema9 = ta.trend.EMAIndicator(close, window=9).ema_indicator().iloc[-1]
        ema21 = ta.trend.EMAIndicator(close, window=21).ema_indicator().iloc[-1]
        ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
        macd = ta.trend.MACD(close).macd_diff()
        macd_prev, macd_now = macd.iloc[-2], macd.iloc[-1]
        rsi = ta.momentum.RSIIndicator(close).rsi()
        rsi_prev, rsi_now = rsi.iloc[-2], rsi.iloc[-1]
        atr = ta.volatility.AverageTrueRange(high, low, close).average_true_range().iloc[-1]
        adx = ta.trend.ADXIndicator(high, low, close).adx().iloc[-1]

        signals = []
        score = 0.0

        # EMA alignment
        if ema9 > ema21 > ema50:
            signals.append("EMA alignment bullish")
            score += 0.8

        # MACD crossover
        if macd_prev < 0 and macd_now > 0:
            signals.append("MACD bullish crossover")
            score += 1.5

        # RSI bounce
        if rsi_now > 40 and rsi_prev < 40:
            signals.append("RSI recovery")
            score += 1.0

        # Volume spike
        if volume.iloc[-1] > 1.8 * volume.iloc[-20:].mean():
            signals.append("Volume spike")
            score += 1.2

        # Market regime bonus
        if adx > 25 and ema9 > ema21:
            score += 0.5

        if score < 1.0:
            return None

        # Entry logic
        strong_trend = adx > 30
        atr_multiplier = 3.0 if strong_trend else 2.0
        entry_price = max(ema21 * 1.003, close.iloc[-1])
        stop_loss = entry_price - atr * atr_multiplier
        take_profit1 = entry_price + (entry_price - stop_loss) * 3
        take_profit2 = entry_price + (entry_price - stop_loss) * 5

        return {
            "symbol": symbol,
            "score": round(score, 2),
            "entry": round(entry_price, 8),
            "stop_loss": round(stop_loss, 8),
            "take_profit1": round(take_profit1, 8),
            "take_profit2": round(take_profit2, 8),
            "risk_reward1": 3,
            "risk_reward2": 5,
            "signals": signals
        }
    except Exception as e:
        print(f"❌ Error analyzing {symbol}: {e}", flush=True)
        return None

# === [4] Performance logging ===
def send_performance_summary():
    print("📊 Performance summary not implemented yet.", flush=True)

def check_and_log_performance(trades):
    end_time = time.time()
    if hasattr(check_and_log_performance, 'start_time'):
        duration = end_time - check_and_log_performance.start_time
        print(f"⏱️ Scan took {duration:.2f} seconds", flush=True)
    else:
        print("⏱️ Scan timing not initialized.", flush=True)
    print(f"📈 {len(trades)} high-conviction trades found", flush=True)

# === [5] Optional config optimization ===
def optimize_config():
    print("🧠 GPT-based config optimization triggered (not implemented)", flush=True)
