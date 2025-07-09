import json
import requests
from datetime import datetime
import streamlit as st

def load_alerts(path="alerts/alerts.json"):
    with open(path) as f:
        data = json.load(f)
    return data.get("tickers", {}), data.get("scanners", [])


def check_alerts(df, config):
    tickers, scanners = load_alerts()
    triggered = []
    st.session_state.setdefault("triggered_alerts", set())

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
            if result is True and key not in st.session_state["triggered_alerts"]:
                triggered.append((alert, row, ticker))
                st.session_state["triggered_alerts"].add(key)
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
                # Only trigger if not already triggered for this ticker
                if "triggered" not in alert:
                    alert["triggered"] = []
                if row_dict.get("Ticker", "") not in alert["triggered"]:
                    triggered.append((alert, row, row_dict.get("Ticker", "")))
                    alert["triggered"].append(row_dict.get("Ticker", ""))

    # Save updated alerts
    with open("alerts/alerts.json", "w") as f:
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
    api_key = config.get("alerts", {}).get("brevo_key")  # Rename in config.yaml

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
