import json
import time
import pandas as pd
import requests
from datetime import datetime
import yaml
import os
import yfinance as yf
import numpy as np

ALERTS_FILE = "alerts/alerts.json"
CONFIG_PATH = "config.yaml"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def load_alerts(path=ALERTS_FILE):
    with open(path) as f:
        data = json.load(f)
    return data.get("tickers", {}), data.get("scanners", [])

def fetch_all_tickers_df():
    watchlists_dir = "watchlists"
    tickers = set()
    for fname in os.listdir(watchlists_dir):
        if fname.endswith(".txt"):
            with open(os.path.join(watchlists_dir, fname)) as f:
                for line in f:
                    t = line.strip().upper()
                    if t:
                        tickers.add(t)
    tickers = list(tickers)
    if not tickers:
        raise ValueError("No tickers found in watchlists.")

    # Download last 30 days for indicators
    df = yf.download(tickers, period="30d", group_by='ticker', threads=True, auto_adjust=True)
    rows = []
    for tkr in tickers:
        try:
            h = df[tkr] if isinstance(df.columns, pd.MultiIndex) else df
            h = h.dropna()
            if len(h) < 15:
                continue

            # Calculate RSI (14)
            delta = h["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            h["RSI"] = rsi

            # Calculate MACD
            ema12 = h["Close"].ewm(span=12, adjust=False).mean()
            ema26 = h["Close"].ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            macd_diff = macd - signal
            h["MACD"] = macd
            h["MACD_diff"] = macd_diff

            last = h.iloc[-1]
            prev_close = h["Close"].iloc[-2] if len(h) >= 2 else None
            percent_change = ((last["Close"] - prev_close) / prev_close) * 100 if prev_close else None


            # Average Volume (last 20 days)
            avg_vol = h["Volume"].rolling(20).mean().iloc[-1] if len(h) >= 20 else h["Volume"].mean()

            # Market Cap and Float from yfinance info
            info = {}
            try:
                yf_ticker = yf.Ticker(tkr)
                info = yf_ticker.info
            except Exception:
                pass
            mcap = info.get("marketCap", None)
            float_shares = info.get("floatShares", None)
            pe_ratio = info.get("trailingPE", None),
            eps = info.get("trailingEps", None)
            


            rows.append({
            "Ticker":        tkr,
            "Price":         last["Close"],
            "RSI":           last["RSI"],
            "MACD":          last["MACD_diff"],
            "Volume":        last["Volume"],
            "Avg Vol":       avg_vol,
            "Market Cap":    mcap,
            "Float":         float_shares,
            "PE Ratio":      pe_ratio,
            "EPS":           eps,
            "PercentChange": percent_change,
        })

        except Exception as e:
            print(f"[Data Error] {tkr}: {e}")
            continue
    result_df = pd.DataFrame(rows)
    return result_df

def check_alerts(df, config):
    tickers, scanners = load_alerts()
    triggered = []
    triggered_alerts = set()  # Local set for daemon

    # ticker alerts
    for ticker, ticker_alerts in list(tickers.items()):
        new_alerts = []
        row = df[df["Ticker"] == ticker]
        if row.empty:
            continue
        row_dict = row.iloc[0].to_dict()

        for alert in ticker_alerts:
            result = alert_eval(alert["expression"], row_dict)
            key = (ticker, alert["expression"])
            if result is True and key not in triggered_alerts:
                print(f"[ALERT] Ticker: {ticker} | Expression: {alert['expression']}")
                triggered.append((alert, row, ticker))
                triggered_alerts.add(key)
            elif isinstance(result, str):
                print(result)
                new_alerts.append(alert)
            else:
                new_alerts.append(alert)

        if new_alerts:
            tickers[ticker] = new_alerts
        else:
            del tickers[ticker]

    # scanner alerts
    for alert in scanners:
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            result = alert_eval(alert["expression"], row_dict)
            key = (alert["id"], row_dict.get("Ticker", ""))
            if result is True:
                if "triggered" not in alert:
                    alert["triggered"] = []
                if row_dict.get("Ticker", "") not in alert["triggered"]:
                    print(f"[ALERT] Scanner: {alert.get('id', '?')} | Ticker: {row_dict.get('Ticker', '')} | Expression: {alert['expression']}")
                    triggered.append((alert, row, row_dict.get("Ticker", "")))
                    alert["triggered"].append(row_dict.get("Ticker", ""))

    # Save updated alerts
    with open(ALERTS_FILE, "w") as f:
        json.dump({"tickers": tickers, "scanners": scanners}, f, indent=4)

    # Send alerts
    for alert, df, ticker in triggered:
        msg = alert["message"]
        channel = alert.get("channel") or alert.get("channels", ["desktop"])[0]
        send_alert(channel, msg, df, ticker, config, alertjson=alert)

def alert_eval(expr_text, row):
    try:
        context = {k.replace(" ", ""): v for k, v in row.items()}
        return eval(expr_text, {}, context)
    except Exception as e:
        return f"[Alert Error] {row.get('Ticker', '???')} -> {e}"

def send_alert(channel, message, df, ticker, config, alertjson=None):
    if channel == "desktop":
        try:
            from plyer import notification
            title = f'🌒 Moon Sniper Alert {datetime.now().strftime("%H:%M:%S")}'

            body = f"{ticker} - {alertjson.get('message', message)}"

            if len(body) > 250:  # Windows limit is 256
                body = body[:247] + "..."

            notification.notify(title=title, message=body)
            print(f"[Desktop Alert] {message} ✅")
        except Exception as e:
            print(f"[Desktop Alert Error] {e}")

    elif channel == "webhook":
        urls = alertjson.get("recipients", []) if alertjson else []
        if not urls:
            urls = config.get("alerts", {}).get("default_webhook", [])
        if isinstance(urls, str):
            urls = [urls]

        content = alertjson.get("message", message)
        username = alertjson.get("username", "Moon Sniper")

        payload = {
            "content": content,
            "username": username
        }

        for url in urls:
            try:
                r = requests.post(url, json=payload)
                if r.status_code not in (200, 204):  # Discord returns 204 on success
                    print(f"[Webhook Error] {r.status_code}: {r.text}")
                else:
                    print(f"[Webhook Alert] {content} ✅ -> {url}")
            except Exception as e:
                print(f"[Webhook Error] {url} -> {e}")
    elif channel == "email":
        send_email(message, df, config, alertjson=alertjson)

def send_email(message, df, config, alertjson=None):
    default_email = config.get("alerts", {}).get("default_email")
    api_key = config.get("alerts", {}).get("brevo_key")

    if not api_key:
        print("[Email Alert] Skipped — no Brevo API key")
        return

    recipients = alertjson.get("email", []) if alertjson else []
    if not recipients and default_email:
        recipients = [default_email]

    subject = "📈 Moon Sniper Alert Triggered"
    body = message

    for email in recipients:
        send_via_brevo(email, subject, message, body, api_key)

def send_via_brevo(to, subject, message, content, api_key):
    try:
        data = {
            "sender": {"name": "Moon Sniper", "email": "skrrtlasagna@gmail.com"},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": content
        }

        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json"
            },
            json=data
        )

        if r.status_code == 201:
            print(f"[Email Sent] {message} ✅")
        else:
            print(f"[Email Error] {r.status_code}: {r.text}")

    except Exception as e:
        print(f"[Brevo Error] {e}")

def main():
    config = load_config()
    print("[Daemon] Starting alerts daemon...")
    while True:
        try:
            df = fetch_all_tickers_df()
            check_alerts(df, config)
            print(f"[Daemon] Alerts checked. {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"[Daemon Error] {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()