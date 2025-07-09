import json
import time
import pandas as pd
import requests
from datetime import datetime
import yaml
import os
import yfinance as yf

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

    # Download data using yfinance (adjust columns as needed)
    df = yf.download(tickers, period="1d", group_by='ticker', threads=True, auto_adjust=True)
    # Flatten MultiIndex if needed and add 'Ticker' column
    rows = []
    for ticker in tickers:
        try:
            row = df[ticker].iloc[-1].to_dict()
            row["Ticker"] = ticker
            rows.append(row)
        except Exception:
            continue
    result_df = pd.DataFrame(rows)
    return result_df

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
            title = f"🌒 Moon Sniper Alert {datetime.now().strftime('%H:%M:%S')}"
            body = f"{ticker} - {alertjson.get('message', message)}"
            if len(body) > 250:
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
                if r.status_code not in (200, 204):
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

def check_alerts(df, config):
    tickers, scanners = load_alerts()
    triggered = []
    # Use a local set for triggered alerts in the daemon
    triggered_alerts = set()

    # --- Ticker Alerts ---
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

    # --- Scanner Alerts ---
    for alert in scanners:
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            result = alert_eval(alert["expression"], row_dict)
            key = (alert["id"], row_dict.get("Ticker", ""))
            if result is True:
                if "triggered" not in alert:
                    alert["triggered"] = []
                if row_dict.get("Ticker", "") not in alert["triggered"]:
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

def main():
    config = load_config()
    print("[Daemon] Starting alerts daemon...")
    while True:
        try:
            df = fetch_all_tickers_df()
            check_alerts(df, config)
            print("[Daemon] Alerts checked.")
        except Exception as e:
            print(f"[Daemon Error] {e}")
        time.sleep(60)  # Check every 60 seconds

if __name__ == "__main__":
    main()