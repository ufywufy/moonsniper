import streamlit as st
import json
import os

ALERTS_FILE = "alerts/alerts.json"

"""
LOAD SAVE
"""
def load_alerts():
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=4)

"""
RESET STATE
"""
def reset_state(channel):
    suffix = f"_{channel}"
    keys_to_clear = [
        f"edit_idx{suffix}",
        f"editing_alert{suffix}",
        f"alert_ticker{suffix}",
        f"alert_expr{suffix}",
        f"alert_msg{suffix}",
        f"alert_username{suffix}",
        f"alert_email{suffix}",
        f"alert_webhook{suffix}",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
    st.session_state["editing"] = False
    st.session_state["editing_alert"] = False
    st.rerun()

def generate_id(ticker=None, platform="webhook"):
    base = ticker.lower() if ticker else "scanner"
    count = 1  # Default
    alerts = st.session_state.get("alerts", {"tickers": {}, "scanners": []})

    # Flatten existing IDs for same base
    existing_ids = []
    if ticker:
        existing_ids = [a["id"] for a in alerts["tickers"].get(ticker.upper(), []) if "id" in a]
    else:
        existing_ids = [a["id"] for a in alerts["scanners"] if "id" in a]

    while f"{base}_{platform}{count}" in existing_ids:
        count += 1

    return f"{base}_{platform}{count}"

"""
PRESAVE CHECKS
"""
def save_alert(view, alert_type, channel, ticker, expr, msg, recipients=None, username=None, edit_idx=None):
    alerts = st.session_state.setdefault("alerts", {"tickers": {}, "scanners": []})

    # Always generate an id if missing
    def ensure_id(alert, ticker, channel):
        if "id" not in alert or not alert["id"]:
            alert["id"] = generate_id(ticker if alert_type == "ticker" else None, channel)

    alert = {
        "expression": expr,
        "message": msg,
        "channel": channel,
    }
    if recipients:
        alert["recipients"] = recipients
    if channel == "webhook" and username:
        alert["username"] = username

    ensure_id(alert, ticker if alert_type == "ticker" else None, channel)

    if alert_type == "ticker":
        ticker = ticker.upper()
        if ticker not in alerts["tickers"]:
            alerts["tickers"][ticker] = []
        if edit_idx is not None:
            # If editing, preserve id if present
            if "id" in alerts["tickers"][ticker][edit_idx]:
                alert["id"] = alerts["tickers"][ticker][edit_idx]["id"]
            else:
                ensure_id(alert, ticker, channel)
            alerts["tickers"][ticker][edit_idx] = alert
        else:
            alerts["tickers"][ticker].append(alert)
    else:
        if edit_idx is not None:
            # If editing, preserve id if present
            if "id" in alerts["scanners"][edit_idx]:
                alert["id"] = alerts["scanners"][edit_idx]["id"]
            else:
                ensure_id(alert, None, channel)
            alerts["scanners"][edit_idx] = alert
        else:
            alerts["scanners"].append(alert)

    # Unified save logic and rerun
    save_alerts(alerts)
    st.success("✅ Alert saved")
    st.session_state.editing = False
    st.session_state.editing_alert = False 
    st.rerun()



"""
RENDER FORM
"""
def render_form(channel):
    suffix = f"_{channel}"
    recipient_key = f"alert_recipients{suffix}" if channel in ("email", "webhook") else None
    alert_type = st.session_state.get("alert_type", "ticker")

    if alert_type == "ticker" and st.session_state.editing != True:
        st.text_input(
            "Ticker",
            value=st.session_state.get(f"alert_ticker{suffix}", ""),
            key=f"alert_ticker{suffix}",
            placeholder="ex: META"
        )

    st.text_input(
        "Expression",
        key=f"alert_expr{suffix}",
        placeholder="ex: RSI < 60 and Volume > 1000000"
    )

    if channel == "webhook":
        st.text_input(
            "Content",
            key=f"alert_msg{suffix}",
            placeholder="@everyone BUY NOW?"
        )
        st.text_input(
            "Username (optional)",
            key=f"alert_username{suffix}",
            placeholder="ex: Moon Sniper"
        )
    else:
        st.text_input(
            "Message",
            key=f"alert_msg{suffix}",
            placeholder="BUY BUY BUY?"
        )

    if recipient_key:
        st.text_area(
            "Recipient(s)",
            key=recipient_key,
            placeholder="One per line",
            height=80
        )


def get_raw_tickers(watchlist_path: str):
    with open(watchlist_path, "r") as f:
        lines = [line.strip().upper() for line in f if line.strip() and not line.startswith("#")]
    return lines

"""
SHOW EDIT MODAL
"""
def show_edit_modal(view, config, wl):
    if not st.session_state.get("editing_alert"):
        return

    idx = st.session_state.get("edit_idx")
    channel = st.session_state.get("edit_channel")
    ticker = st.session_state.get("edit_ticker", "").strip().upper()

    alerts = load_alerts()

    # Determine alert type
    alert_type = "scanner" if ticker.lower() == "scanner" else "ticker"

    # Initialize empty alert for new creation
    if idx is None or st.session_state.editing == False:
        alert = {
            "id": None,
            "expression": "",
            "message": "",
            "channel": channel,
        }
        if alert_type == "ticker":
            alert["ticker"] = ticker
        if channel in ("email", "webhook"):
            alert["recipients"] = []
        if channel == "webhook":
            alert["username"] = ""
    else:
        # Editing an existing alert
        try:
            if alert_type == "scanner":
                alert = alerts["scanners"][idx]
            else:
                alert = alerts["tickers"][ticker][idx]
        except Exception as e:
            print(e)
            st.error("❌ Could not load alert for editing.")
            return

    # Store values in session state
    st.session_state["alert_type"] = alert_type
    suffix = f"_{channel}"
    if f"alert_expr{suffix}" not in st.session_state:
        st.session_state[f"alert_expr{suffix}"] = alert.get("expression", "")
    if f"alert_msg{suffix}" not in st.session_state:
        st.session_state[f"alert_msg{suffix}"] = alert.get("message", "")
    if f"alert_ticker{suffix}" not in st.session_state:
        st.session_state[f"alert_ticker{suffix}"] = ticker if alert_type == "ticker" else ""


    if channel in ("email", "webhook"):
        key = f"alert_recipients{suffix}"
        if key not in st.session_state:
            st.session_state[key] = "\n".join(alert.get("recipients", []))
    if channel == "webhook":
        key = f"alert_username{suffix}"
        if key not in st.session_state:
            st.session_state[key] = alert.get("username", "")

    st.subheader(f"🔔 {'Edit' if idx is not None else 'New'} {channel.title()} Alert")

    with st.form(f"alert_form_{channel}"):
        render_form(channel)
        switch_clicked = False
        col1, col2, col3 = st.columns(3)
        save_clicked = col1.form_submit_button("✅ Save Alert")
        cancel_clicked = col2.form_submit_button("❌ Cancel")
        if st.session_state.editing == False:
            switch_clicked = col3.form_submit_button(
                "🔀 Switch to scanner alert" if alert_type == "ticker" else "🔀 Switch to ticker alert"
            )

    if save_clicked:
        expr = st.session_state.get(f"alert_expr{suffix}", "").strip()
        msg = st.session_state.get(f"alert_msg{suffix}", "").strip()
        ticker_val = st.session_state.get(f"alert_ticker{suffix}", "").strip()
        recipients = st.session_state.get(f"alert_recipients{suffix}", "").splitlines() if channel in ("email", "webhook") else []
        username = st.session_state.get(f"alert_username{suffix}", "").strip() if channel == "webhook" else None
        test = view.expr(expr)
        if alert_type == "ticker" and ticker_val.upper() not in wl:
            st.error(f"❌ Ticker '{ticker_val.upper()}' not found in watchlist file.")
            return
        if test is False:
            st.error("Invalid expression. Please check syntax and try again.")
            return
    # Don't reset state if the form is incomplete!
        elif alert_type == "ticker" and (not ticker_val or not expr or not msg):
            st.warning("⚠️ Ticker, expression, and message are required for ticker alerts.")
            return

        elif alert_type == "scanner" and (not expr or not msg):
            st.warning("⚠️ Expression and message are required for scanner alerts.")
            return

        else:
            # Only now that validation passed, save and reset
            save_alert(view, alert_type, channel, ticker_val, expr, msg, recipients, username, idx)
            st.session_state["editing_alert"] = False


    elif cancel_clicked:
        reset_state(channel)

    elif switch_clicked:
        st.session_state["edit_ticker"] = "" if alert_type == "scanner" else "scanner"
        st.rerun()