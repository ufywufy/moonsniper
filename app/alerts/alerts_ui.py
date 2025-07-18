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

    if "alerts" not in st.session_state:
        st.session_state["alerts"] = load_alerts()

    alerts = st.session_state["alerts"]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧬 Export DNA", key="export_dna_alert"):
            export_dna("alert")
    with col2:
        if st.button("🧬 Import DNA", key="import_dna_alert"):
            st.session_state["show_import_alert"] = True

    if st.session_state.get("show_import_alert"):
        dna_input = st.text_area(
            "Paste DNA alert strings (one per line):",
            height=150,
            placeholder="ex: ms:alert,AAPL,RSI > 90,desktop,message:df"
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Import", key="confirm_import_alert"):
                import_dna("alert", dna_input)
                st.session_state["show_import_alert"] = False
                st.rerun()
        with c2:
            if st.button("❌ Cancel", key="cancel_import_alert"):
                st.session_state["show_import_alert"] = False
                st.rerun()

    for tab, channel in zip(st.tabs(["Emails", "Webhooks", "Desktop"]), ["email", "webhook", "desktop"]):
        with tab:
            render_alert_tab(view, alerts, channel, config, wl)


def render_alert_tab(view, alerts, channel, config, wl):
    st.markdown(f"#### 📋 Active {channel} alerts")

    if st.button("➕ New Alert", key=f"add_alert_{channel}"):
        st.session_state.update({
            "editing_alert": True,
            "edit_channel": channel,
            "edit_ticker": "",
            "alert_type": "ticker",
            "editing": False,
            "edit_idx": None
        })

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

    # Ticker Alerts
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
                if st.button("✏️", key=f"edit_{channel}_{ticker}_{i}"):
                    st.session_state.update({
                        "editing_alert": True,
                        "editing": True,
                        "edit_channel": channel,
                        "edit_idx": i,
                        "edit_ticker": ticker
                    })
                if st.button("🗑️", key=f"delete_{channel}_{ticker}_{i}"):
                    alerts["tickers"][ticker].pop(i)
                    if not alerts["tickers"][ticker]:
                        del alerts["tickers"][ticker]
                    save_alerts(alerts)
                    st.success(f"🗑️ Deleted alert for {ticker}")
                    st.rerun()

    # Scanner Alerts
    for i, alert in enumerate(alerts.get("scanners", [])):
        if alert.get("channel") != channel:
            continue
        col1, col2, col3 = st.columns([2, 4, 2])
        with col1:
            st.markdown("*scanner*")
        with col2:
            st.markdown(alert.get("expression", ""))
        with col3:
            if st.button("✏️", key=f"edit_{channel}_scanner_{i}"):
                st.session_state.update({
                    "editing_alert": True,
                    "editing": True,
                    "edit_channel": channel,
                    "edit_idx": i,
                    "edit_ticker": "scanner"
                })
            if st.button("🗑️", key=f"delete_{channel}_scanner_{i}"):
                alerts["scanners"].pop(i)
                save_alerts(alerts)
                st.success("🗑️ Deleted scanner alert")
                st.rerun()

    if st.session_state.get("editing_alert") and st.session_state.get("edit_channel") == channel:
        show_edit_modal(view, config, wl)