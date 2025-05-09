# main.py

import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request
import json
import openai
import pandas as pd

from config import CONFIG
from scanner_core import scan_altcoins
from utils import send_telegram_message, optimize_config
from trade_logger import init_trade_log, log_trades

# Initialize the CSV for simulated trades
init_trade_log()

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route("/optimize", methods=["POST"])
def optimize_route():
    """
    Calls your GPT-based optimizer (in utils.optimize_config),
    sends a Telegram summary, and returns the new params.
    """
    try:
        new_params = optimize_config()
        send_telegram_message(f"⚙️ Config optimized: {json.dumps(new_params)}")
        return jsonify({"optimized_params": new_params}), 200
    except Exception as e:
        send_telegram_message(f"❌ Error during optimization: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/analyze", methods=["GET"])
def analyze_route():
    """
    Reads simulated_trades.csv and returns performance summaries:
    - overall metrics
    - by signal_combo
    - by market_regime
    """
    try:
        df = pd.read_csv("simulated_trades.csv")
        total = len(df)
        wins = int((df["outcome"] == "win").sum())
        losses = int((df["outcome"] == "loss").sum())
        pendings = int((df["outcome"] == "pending").sum())
        win_rate = round(wins / total, 3) if total else None
        avg_rr = round(df["rr_ratio"].dropna().mean(), 3) if not df["rr_ratio"].dropna().empty else None

        # Aggregate by signal_combo
        signal_stats = {}
        for combo, group in df.groupby("signal_combo"):
            ct = len(group)
            w = int((group["outcome"] == "win").sum())
            l = int((group["outcome"] == "loss").sum())
            p = int((group["outcome"] == "pending").sum())
            signal_stats[combo] = {
                "count": ct,
                "wins": w,
                "losses": l,
                "pending": p,
                "win_rate": round(w / ct, 3) if ct else None,
                "avg_rr": round(group["rr_ratio"].dropna().mean(), 3) if not group["rr_ratio"].dropna().empty else None
            }

        # Aggregate by market_regime
        regime_stats = {}
        for regime, group in df.groupby("market_regime"):
            ct = len(group)
            w = int((group["outcome"] == "win").sum())
            l = int((group["outcome"] == "loss").sum())
            p = int((group["outcome"] == "pending").sum())
            regime_stats[regime] = {
                "count": ct,
                "wins": w,
                "losses": l,
                "pending": p,
                "win_rate": round(w / ct, 3) if ct else None,
                "avg_rr": round(group["rr_ratio"].dropna().mean(), 3) if not group["rr_ratio"].dropna().empty else None
            }

        summary = {
            "overall": {
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "pending": pendings,
                "win_rate": win_rate,
                "avg_rr": avg_rr
            },
            "by_signal_combo": signal_stats,
            "by_market_regime": regime_stats
        }

        return jsonify(summary), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def background_scan_loop():
    """
    Runs forever: every CONFIG['scan_interval'] seconds runs a full scan,
    logs the top 5 simulated trades, and pushes a Telegram alert for the #1 signal.
    """
    interval = CONFIG.get("scan_interval", 300)
    while True:
        try:
            results = scan_altcoins()  # returns list of dicts with keys:
                                       #   symbol, score, entry, tp, sl,
                                       #   last_price, signal_combo, regime, trend_strength

            if not results:
                time.sleep(interval)
                continue

            # 1) Simulate & log top 5 trades
            top5 = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:5]
            to_log = []
            for r in top5:
                entry = r.get("entry")
                tp    = r.get("tp")
                sl    = r.get("sl")
                last  = r.get("last_price")

                # Determine outcome
                if last is None:
                    outcome = "pending"
                elif tp is not None and last >= tp:
                    outcome = "win"
                elif sl is not None and last <= sl:
                    outcome = "loss"
                else:
                    outcome = "pending"

                # Compute R:R
                rr = None
                if entry is not None and tp is not None and sl is not None and (entry - sl) != 0:
                    rr = (tp - entry) / (entry - sl)

                to_log.append({
                    "timestamp":     datetime.utcnow().isoformat(),
                    "symbol":        r.get("symbol"),
                    "entry_price":   entry,
                    "tp_price":      tp,
                    "sl_price":      sl,
                    "outcome":       outcome,
                    "signal_combo":  r.get("signal_combo"),
                    "rr_ratio":      round(rr, 3) if rr is not None else None,
                    "market_regime": r.get("regime"),
                    "trend_strength":r.get("trend_strength"),
                })

            log_trades(to_log)

            # 2) Send Telegram alert for the top 1 signal
            top = top5[0]
            msg = (
                f"🔍 [{datetime.utcnow().isoformat()}] Top signal:\n"
                f"Symbol: {top.get('symbol')}\n"
                f"Score: {top.get('score'):.2f}\n"
                f"Entry: {top.get('entry')}, TP: {top.get('tp')}, SL: {top.get('sl')}"
            )
            send_telegram_message(msg)

        except Exception as err:
            # Catch-all so one failure doesn't kill the loop
            send_telegram_message(f"❌ Scan loop error: {err}")

        time.sleep(interval)

if __name__ == "__main__":
    # Start background scanner
    thread = threading.Thread(target=background_scan_loop, daemon=True)
    thread.start()

    # Launch Flask API
    port = CONFIG.get("port", 5000)
    app.run(host="0.0.0.0", port=port)
