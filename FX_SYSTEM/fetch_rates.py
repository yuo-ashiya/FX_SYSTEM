"""
GitHub Actionsから定期実行され、通貨ペアの最新値を rates.json に書き出すスクリプト。
GitHub Pages側の index.html はこの rates.json を読み込むだけ(静的配信)。
"""

import json
import time
import datetime
import yfinance as yf

PAIRS = [
    "USD/JPY", "EUR/JPY", "GBP/JPY", "AUD/JPY",
    "EUR/USD", "GBP/USD", "AUD/USD", "EUR/GBP",
    "CHF/TRY", "TRY/JPY", "CHF/MXN", "MXN/JPY",
]

BASE_TICKERS = [
    "USDJPY=X", "EURUSD=X", "GBPUSD=X", "AUDUSD=X",
    "USDCHF=X", "USDTRY=X", "USDMXN=X",
]

OUTPUT_FILE = "rates.json"


def fetch_base_rates():
    data = yf.download(
        tickers=" ".join(BASE_TICKERS),
        period="1d",
        interval="1m",
        progress=False,
        group_by="ticker",
        auto_adjust=True,
    )

    result = {}
    for t in BASE_TICKERS:
        val = None
        try:
            series = data[t]["Close"].dropna()
            if len(series) > 0:
                val = float(series.iloc[-1])
        except Exception:
            try:
                series = data["Close"].dropna()
                if len(series) > 0:
                    val = float(series.iloc[-1])
            except Exception:
                val = None
        result[t] = val
    return result


def compute_pairs(base):
    usdjpy = base.get("USDJPY=X")
    eurusd = base.get("EURUSD=X")
    gbpusd = base.get("GBPUSD=X")
    audusd = base.get("AUDUSD=X")
    usdchf = base.get("USDCHF=X")
    usdtry = base.get("USDTRY=X")
    usdmxn = base.get("USDMXN=X")

    def mul(a, b):
        return a * b if (a is not None and b is not None) else None

    def div(a, b):
        return a / b if (a is not None and b) else None

    return {
        "USD/JPY": usdjpy,
        "EUR/JPY": mul(eurusd, usdjpy),
        "GBP/JPY": mul(gbpusd, usdjpy),
        "AUD/JPY": mul(audusd, usdjpy),
        "EUR/USD": eurusd,
        "GBP/USD": gbpusd,
        "AUD/USD": audusd,
        "EUR/GBP": div(eurusd, gbpusd),
        "CHF/TRY": div(usdtry, usdchf),
        "TRY/JPY": div(usdjpy, usdtry),
        "CHF/MXN": div(usdmxn, usdchf),
        "MXN/JPY": div(usdjpy, usdmxn),
    }


def main():
    base = fetch_base_rates()
    pairs = compute_pairs(base)

    out = {
        "rates": pairs,
        "updated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at_epoch": int(time.time()),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("Wrote", OUTPUT_FILE, out["updated_at_utc"])


if __name__ == "__main__":
    main()
