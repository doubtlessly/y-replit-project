# trade_logger.py
import csv
from datetime import datetime
from typing import Dict, List

LOG_FILE = "simulated_trades.csv"
FIELDNAMES = [
    "timestamp", "symbol", "entry_price", "tp_price", "sl_price",
    "outcome",        # "win" | "loss" | "pending"
    "signal_combo",   # e.g. "ma_cross+rsi_div"
    "rr_ratio",       # float
    "market_regime",  # e.g. "bull", "bear", "sideways"
    "trend_strength"  # float or categorical
]

# ensure header exists
def init_trade_log():
    try:
        with open(LOG_FILE, "x", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
    except FileExistsError:
        pass

def log_trades(trades: List[Dict]):
    """
    Appends a list of trade dicts to the CSV.
    Each dict must have exactly the keys in FIELDNAMES.
    """
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        for trade in trades:
            writer.writerow(trade)
