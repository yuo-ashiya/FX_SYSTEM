"""
GitHub Actionsから定期実行され、通貨ペアの最新値を rates.json に書き出すスクリプト。
GitHub Pages側の index.html はこの rates.json を読み込むだけ(静的配信)。

さらに、data.json に保存されているアラート上限/下限を読み取り、
現在値がその範囲を超えた「瞬間」に ntfy.sh 経由でスマホへプッシュ通知を送る。
"""

import json
import os
import time
import datetime
import urllib.request
import urllib.error
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

RATES_FILE = "rates.json"
DATA_FILE = "data.json"          # 手入力データ(アラート上限/下限を含む)
ALERT_STATE_FILE = "alert_state.json"  # 前回時点での各ペアのアラート状態

# GitHub Actionsのリポジトリ変数として設定する(NTFY_TOPIC)。未設定なら通知は送らない。
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()


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


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: {path} の読み込みに失敗しました: {e}")
            return default
    return default


def parse_float(s):
    try:
        if s is None or s == "":
            return None
        return float(s)
    except (TypeError, ValueError):
        return None


def send_ntfy(message):
    """ntfy.sh 経由でプッシュ通知を送る。NTFY_TOPIC未設定なら何もしない。"""
    if not NTFY_TOPIC:
        print("NTFY_TOPIC未設定のため通知はスキップします")
        return
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    try:
        req = urllib.request.Request(
            url,
            data=message.encode("utf-8"),
            headers={"Title": "FX Alert", "Priority": "high"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        print("ntfy通知を送信しました:", message)
    except Exception as e:
        print("ntfy通知の送信に失敗しました:", e)


def check_alerts(rates, thresholds, prev_state):
    """
    各ペアについて 現在値 vs アラート上限/下限 を判定し、
    「範囲外に入った瞬間」と「範囲内に戻った瞬間」だけメッセージを作る。
    """
    new_state = {}
    messages = []

    for pair, val in rates.items():
        t = thresholds.get(pair, {}) or {}
        upper = parse_float(t.get("upper"))
        lower = parse_float(t.get("lower"))

        status = "normal"
        if val is not None:
            if upper is not None and val > upper:
                status = "over"
            elif lower is not None and val < lower:
                status = "under"

        new_state[pair] = status
        prev = prev_state.get(pair, "normal")

        if status != "normal" and status != prev:
            if status == "over":
                messages.append(f"{pair}: 上限 {upper} を超えました(現在値 {val:.5f})")
            else:
                messages.append(f"{pair}: 下限 {lower} を下回りました(現在値 {val:.5f})")
        elif status == "normal" and prev != "normal":
            messages.append(f"{pair}: アラート範囲内に戻りました(現在値 {val:.5f})")

    return new_state, messages


def main():
    base = fetch_base_rates()
    pairs = compute_pairs(base)

    out = {
        "rates": pairs,
        "updated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at_epoch": int(time.time()),
    }

    with open(RATES_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("Wrote", RATES_FILE, out["updated_at_utc"])

    # --- アラート判定・通知 ---
    thresholds = load_json(DATA_FILE, {})
    prev_state = load_json(ALERT_STATE_FILE, {})

    new_state, messages = check_alerts(pairs, thresholds, prev_state)

    if messages:
        send_ntfy("\n".join(messages))
    else:
        print("アラート状態の変化はありません")

    with open(ALERT_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)

    print("Wrote", ALERT_STATE_FILE)


if __name__ == "__main__":
    main()
