import streamlit as st
import json
import os
from alerts.alerts_edit import show_edit_modal
from core.dna import export_dna, import_dna
ALERTS_FILE = "alerts/alerts.json"

def load_alerts():
    if not os.path.exists(ALERTS_FILE):
        return {"tickers": {}, "scanners": []}
    with open(ALERTS_FILE, "r") as f:
        return json.load(f)

def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)

def show_alert_modal(view, config, wl):
    st.markdown("### 🔔 Alerts")

    alerts = st.session_state.get("alerts", load_alerts())
    st.session_state["alerts"] = alerts  # always store in session

    col_alert1, col_alert2 = st.columns([1, 1])
    with col_alert1:
        if st.button("🧬 Export DNA", key="export_dna_alert"):
            export_dna("alert")
    with col_alert2:
        if st.button("🧬 Import DNA", key="import_dna_alert"):
            st.session_state["show_import_alert"] = True
    if "show_import_alert" not in st.session_state:
        st.session_state["show_import_alert"] = False
    if st.session_state.show_import_alert:
        dna_alert_input = st.text_area("Paste DNA alert strings (one per line):", height=150, placeholder="ex: ms:alert,AAPL,RSI > 90,desktop,message:df")
        col1, col2 = st.columns([1, 1])  # Adjust width ratio if needed

        with col1:
            if st.button("💾 Import", key="confirm_import_alert"):
                st.session_state["show_import_alert"] = False
                import_dna("alert", dna_alert_input)
                st.rerun()

        with col2:
            if st.button("❌ Cancel", key="cancel_import_alert"):
                st.session_state["show_import_alert"] = False
                st.rerun()


    tabs = st.tabs(["Emails", "Webhooks", "Desktop"])
    channels = ["email", "webhook", "desktop"]

    for tab, channel in zip(tabs, channels):
        with tab:
            render_alert_tab(view, alerts, channel, config, wl)

def render_alert_tab(view, alerts, channel, config, wl):
    st.markdown(f"#### 📋 Active {channel} alerts")

    # New alert button (opens blank modal)
    col_add, _ = st.columns([1, 9])
    with col_add:
        if st.button("➕", key=f"add_alert_btn_{channel}"):
            st.session_state["editing_alert"] = True
            st.session_state["edit_channel"] = channel
            st.session_state["edit_ticker"] = ""  # empty string = ticker by default
            st.session_state["alert_type"] = "ticker"  # set this explicitly
            st.session_state["editing"] = False
            st.session_state["edit_idx"] = None

    # Table header
    st.markdown("""
    <style>
        .alert-header, .alert-row {
            display: flex;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #444;
        }
        .col-ticker { flex: 2; }
        .col-expression { flex: 4; }
        .col-actions { flex: 2; text-align: right; }
    </style>
    <div class="alert-header">
        <div class="col-ticker">Ticker</div>
        <div class="col-expression">Expression</div>
    </div>
    """, unsafe_allow_html=True)

    # ticker alerts
    for ticker, ticker_alerts in alerts.get("tickers", {}).items():
        for i, alert in enumerate(ticker_alerts):
            if alert.get("channel") != channel:
                continue

            col1, col2, col3 = st.columns([2, 4, 2])
            with col1:
                st.markdown(f"**{ticker}**")
            with col2:
                st.markdown(alert.get("expression", ""))
            with col3:
                if st.button("✏️", key=f"edit_ticker_{channel}_{ticker}_{i}"):
                    st.session_state["editing_alert"] = True
                    st.session_state["edit_channel"] = channel
                    st.session_state["edit_idx"] = i
                    st.session_state["edit_ticker"] = ticker
                    st.session_state["editing"] = True
                if st.button("🗑️", key=f"delete_ticker_{channel}_{ticker}_{i}"):
                    del alerts["tickers"][ticker][i]
                    if not alerts["tickers"][ticker]:  # if empty, remove ticker key entirely
                        del alerts["tickers"][ticker]
                    save_alerts(alerts)
                    st.success(f"🗑️ Alert for {ticker} deleted.")
                    st.rerun()

    # scanner alerts
    for i, alert in enumerate(alerts.get("scanners", [])):
        if alert.get("channel") != channel:
            continue

        col1, col2, col3 = st.columns([2, 4, 2])
        with col1:
            st.markdown("*scanner*")
        with col2:
            st.markdown(alert.get("expression", ""))
        with col3:
            if st.button("✏️", key=f"edit_scanner_{channel}_{i}"):
                st.session_state["editing_alert"] = True
                st.session_state["editing"] = True
                st.session_state["edit_channel"] = channel
                st.session_state["edit_idx"] = i
                st.session_state["edit_ticker"] = "scanner"
            if st.button("🗑️", key=f"delete_scanner_{channel}_{i}"):
                del alerts["scanners"][i]
                save_alerts(alerts)
                st.success("🗑️ Scanner alert deleted.")
                st.rerun()
    if st.session_state.get("editing_alert") and st.session_state.get("edit_channel") == channel:
        show_edit_modal(view, config, wl)