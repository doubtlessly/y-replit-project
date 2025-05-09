# utils.py

import os
import json
import requests
import pandas as pd
import openai
from typing import Dict, List, Union
import ccxt
from config import CONFIG


def send_telegram_message(text: str) -> None:
    """
    Sends a message to your configured Telegram chat.
    """
    token = CONFIG.get("telegram_token")
    chat_id = CONFIG.get("telegram_chat_id")
    if not token or not chat_id:
        raise ValueError("Missing Telegram configuration")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=payload)
    resp.raise_for_status()


def fetch_market_data(symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
    """
    Fetches OHLCV data for a symbol using the exchange specified in CONFIG
    (default 'mexc') and returns a DataFrame. Symbols without a slash
    will default to the quote currency (e.g. 'USDT').

    Adds debug logs to ensure correct exchange instantiation and symbol normalization.
    """
    # Resolve exchange name
    exch = CONFIG.get("exchange", "mexc")
    # Ensure string
    if not isinstance(exch, str):
        # If user mistakenly stored a class/object
        exch = getattr(exch, 'id', None) or getattr(exch, '__name__', str(exch)).lower()
    exch_name = exch.lower()
    print(f"[DEBUG] exch_name={exch_name!r}, type={type(exch_name)}")

    # Get ccxt exchange class
    if not hasattr(ccxt, exch_name):
        raise ValueError(f"Unsupported exchange '{exch_name}' in CONFIG")
    exchange_cls = getattr(ccxt, exch_name)

    # Prepare credentials
    creds: Dict[str, str] = {}
    api_key = CONFIG.get(f"{exch_name}_api_key")
    secret = CONFIG.get(f"{exch_name}_api_secret")
    if api_key:
        creds["apiKey"] = api_key
    if secret:
        creds["secret"] = secret

    # Instantiate exchange
    try:
        exchange = exchange_cls(creds)
    except Exception as e:
        raise RuntimeError(f"Failed to init {exch_name} exchange: {e}")
    print(f"[DEBUG] exchange instance={exchange}, type={type(exchange)}")

    # Load markets once
    if not getattr(exchange, 'markets', None):
        exchange.load_markets()

    # Normalize symbol to include quote if missing
    if "/" not in symbol:
        base = symbol.upper()
        quote = CONFIG.get("quote_currency", "USDT").upper()
        symbol = f"{base}/{quote}"
    print(f"[DEBUG] normalized symbol={symbol}")

    # Validate symbol
    if symbol not in exchange.markets:
        raise ValueError(f"{exch_name} does not have market symbol {symbol}")

    # Fetch OHLCV
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["symbol"] = symbol
    return df


def analyze_coin(df: pd.DataFrame) -> Dict:
    """
    Example analysis: computes RSI-based score, entry/TP/SL levels, regime, and trend strength.
    """
    import ta
    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    latest = df.iloc[-1]
    score = 100 - latest["rsi"]
    entry = latest["close"] * (1 - CONFIG.get("entry_buffer", 0.01))
    tp = latest["close"] * (1 + CONFIG.get("tp_multiplier", 0.02))
    sl = latest["close"] * (1 - CONFIG.get("sl_multiplier", 0.03))
    regime = (
        "bull"
        if df["close"].pct_change().rolling(50).mean().iloc[-1] > 0
        else "bear"
    )
    trend_strength = abs(df["close"].pct_change().rolling(5).mean().iloc[-1])
    signal_combo = "rsi_reversal"
    return {
        "symbol": df["symbol"].iloc[0],
        "score": score,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "last_price": latest["close"],
        "signal_combo": signal_combo,
        "regime": regime,
        "trend_strength": trend_strength,
    }


def optimize_config() -> Dict:
    """
    Auto-tunes configuration parameters based on historical simulated trades.

    Loads `simulated_trades.csv`, summarizes performance, queries GPT for
    new parameter values, and saves them to `dynamic_config.json`.
    """
    df = pd.read_csv("simulated_trades.csv")
    total = len(df)
    wins = int((df["outcome"] == "win").sum())
    win_rate = wins / total if total else 0.0
    avg_rr = float(df["rr_ratio"].dropna().mean()) if not df["rr_ratio"].dropna().empty else 0.0

    prompt = f"""
You are a trading strategy optimizer.

Recent performance:
- Total trades: {total}
- Win rate: {win_rate:.3f}
- Avg R:R: {avg_rr:.3f}

Current configuration values:
- score_threshold: {CONFIG.get('score_threshold')}
- atr_multiplier: {CONFIG.get('atr_multiplier')}
- top_coins_limit: {CONFIG.get('top_coins_limit')}

Suggest improved numeric values for these parameters to enhance win rate and reward-to-risk.
Return the suggestions as a JSON object with keys:
"score_threshold", "atr_multiplier", "top_coins_limit"
"""

    openai.api_key = CONFIG.get("openai_api_key")
    response = openai.ChatCompletion.create(
        model=CONFIG.get("openai_model", "gpt-4-mini"),
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=CONFIG.get("openai_temperature", 0.7)
    )
    content = response.choices[0].message.content.strip()

    try:
        new_params = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON from GPT: {content}")

    with open("dynamic_config.json", "w") as f:
        json.dump(new_params, f, indent=2)

    return new_params
