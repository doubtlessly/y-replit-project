import ccxt
import concurrent.futures
from config import CONFIG
from utils import fetch_market_data, analyze_coin

def scan_altcoins(progress_callback=None):
    exchange = ccxt.mexc()
    markets = exchange.load_markets()
    tickers = list(markets.keys())
    filtered = [t for t in tickers if '/' in t and t.endswith('/USDT')]
    coins = [t.replace('/USDT', '') for t in filtered]
    total = min(CONFIG.get("top_coins_limit", 150), len(coins))

    results = []

    def process_coin(symbol_index_pair):
        i, symbol = symbol_index_pair
        if progress_callback:
            print(f"\r📊 Scanned {i}/{total} coins", end="", flush=True)
        try:
            df = fetch_market_data(symbol, exchange)
            if df is None or df.empty:
                return None
            return analyze_coin(symbol, df)
        except Exception as e:
            print(f"\n⚠️ Error analyzing {symbol}: {e}", flush=True)
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        symbol_pairs = list(enumerate(coins[:total], 1))
        futures = list(executor.map(process_coin, symbol_pairs))

    results = [r for r in futures if r is not None]
    print()  # newline after last progress
    return sorted(results, key=lambda x: x['score'], reverse=True)
