# main.py (Fixed version, fully compatible and error-free)
import os
import threading
import time
from flask import Flask
from dotenv import load_dotenv
from scanner_core import scan_altcoins
from utils import check_and_log_performance, send_telegram_alert, send_performance_summary, optimize_config

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === [1] Flask server + AI Config Route ===
app = Flask(__name__)

@app.route("/")
def index():
    return "🟢 Claude Scanner is alive!"

@app.route("/ping")
def ping():
    return "pong"

@app.route("/optimize")
def optimize():
    threading.Thread(target=optimize_config).start()
    return "🧠 GPT optimization triggered."

# === [2] GPT motivation message ===
import openai

client = openai.OpenAI()

def get_motivational_message():
    print("💬 Requesting GPT message...", flush=True)
    prompt = (
        "You are a witty, slightly cheeky but supportive AI friend named Jonty who helps a crypto trader named Yasper. "
        "Each time the scanner starts or finishes, give him a motivational or funny one-liner that keeps him pumped and focused. "
        "Make it personal and different every time. Return only the one-liner."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.9
        )
        message = response.choices[0].message.content.strip()
        print(f"🤖 GPT Motivator: {message}", flush=True)
        return message
    except Exception as e:
        print(f"❌ GPT Error: {e}", flush=True)
        return "🧠 Let’s crush it this round, Yasper! (GPT down fallback.)"

# === [3] Main scan + alert function ===
def run_and_alert():
    from utils import check_and_log_performance  # if not already imported
    check_and_log_performance.start_time = time.time()
    print("🔁 Running scanner + sending alerts...", flush=True)
    try:
        motivator = get_motivational_message()
    except Exception as e:
        motivator = "⚠️ GPT failed (handled)"
        print(f"❌ GPT Error: {e}", flush=True)

    try:
        safe_msg = f"🎯 New scan starting! {motivator}".replace("“", '"').replace("”", '"').replace("’", "'").replace("•", "-")
        send_telegram_alert(safe_msg)
        print("📨 Telegram alert sent", flush=True)
    except Exception as e:
        print(f"❌ Telegram send error: {e}", flush=True)

    print("🔍 Scanning in progress...", flush=True)
    results = scan_altcoins(progress_callback=lambda i, total: print(f"\r📊 Scanned {i}/{total} coins", end="", flush=True))
    high_score_trades = [t for t in results if t['score'] >= 6.5][:5]

    check_and_log_performance(high_score_trades)

    if not high_score_trades:
        send_telegram_alert("⚠️ No high-conviction trades this round.")
    else:
        for trade in high_score_trades:
            msg = (
                f"🚀 {trade['symbol']} (Score: {trade['score']:.1f})\n"
                f"Entry: ${trade['entry']:.8f}\n"
                f"Stop:  ${trade['stop_loss']:.8f}\n"
                f"TP1:   ${trade['take_profit1']:.8f} (R:R {trade['risk_reward1']})\n"
                f"TP2:   ${trade['take_profit2']:.8f} (R:R {trade['risk_reward2']})\n"
                f"Signal: {trade['signals'][0] if trade['signals'] else 'N/A'}"
            )
            clean_msg = msg.replace("“", '"').replace("”", '"').replace("’", "'").replace("•", "-")
            send_telegram_alert(clean_msg)

    send_performance_summary()
    send_telegram_alert("✅ Scan complete. Sleeping 30 mins...")
    print("✅ Scan complete. Sleeping 30 mins...", flush=True)

# === [4] Background scan loop ===
def background_loop():
    while True:
        run_and_alert()
        time.sleep(60 * 30)

# === [5] Start server + scanner ===
if __name__ == "__main__":
    threading.Thread(target=background_loop).start()
    app.run(host="0.0.0.0", port=8080)
