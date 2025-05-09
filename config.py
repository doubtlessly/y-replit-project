import json

DEFAULT_CONFIG = {
    "exchange": "mexc",
    "market_type": "spot",
    "top_coins_limit": 150,
    "excluded_coins": ["BTC", "ETH", "USDT", "USDC", "BUSD", "DAI", "TUSD"],
    "timeframes": ["15m", "1h", "4h"],
    "tf_weights": {"15m": 0.2, "1h": 0.35, "4h": 0.45},
    "ohlcv_limit": 200,
    "min_score": 4,
    "risk_percent": 1,
    "leverage": 10,
    "min_volume_usd": 5_000_000,
    "starting_balance": 100,
    "signal_weights": {
        "EMA alignment bullish": 0.8,
        "EMA9 crossed above EMA21": 1.0,
        "RSI bullish divergence": 2.5,
        "MACD bullish crossover": 1.5,
        "Volume spike": 1.2,
    },
}

def load_dynamic_config():
    try:
        with open("dynamic_config.json", "r") as f:
            dynamic = json.load(f)
            merged = {**DEFAULT_CONFIG, **dynamic}
            if "tf_weights" in dynamic:
                merged["tf_weights"] = {**DEFAULT_CONFIG["tf_weights"], **dynamic["tf_weights"]}
            if "signal_weights" in dynamic:
                merged["signal_weights"] = {**DEFAULT_CONFIG["signal_weights"], **dynamic["signal_weights"]}
            return merged
    except Exception:
        return DEFAULT_CONFIG

CONFIG = load_dynamic_config()
