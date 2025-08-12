import streamlit as st
import yfinance as yf
import pandas as pd
import yaml
from datetime import datetime, timedelta
import pytz
from alerts.alerts import check_alerts
import logging
import sys
import json
from core.dna import export_dna, import_dna
import re, os


# Core functionality
from core.watchlist.watchlistdf import WatchlistDf
from core.watchlist.watchlistview import WatchlistView
from core.watchlist.watchlistgrid import WatchlistGrid
from core.yaml_picks import YamlPicks

# Chart UI
from ui.chart import Chart
from core.news import get_news
from alerts.alerts_ui import show_alert_modal  # new import for alert modal
from streamlit_autorefresh import st_autorefresh

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("log.txt", mode="a", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Optional: still shows in terminal
    ]
)
def _moves_snapshot(df: pd.DataFrame) -> dict:
    # keep only the columns we need
    cols = [c for c in ["Ticker", "Price", "Volume", "RSI"] if c in df.columns]
    if not cols:
        return {"values": {}}

    snap = df[cols].copy()

    # drop rows without a ticker and dedupe by ticker (keep the last one)
    snap = snap.dropna(subset=["Ticker"])
    snap = snap.drop_duplicates(subset=["Ticker"], keep="last")

    # build { TICKER: {Price, Volume, RSI} }
    values = {
        row["Ticker"]: {
            k: row[k] for k in ["Price", "Volume", "RSI"] if k in snap.columns
        }
        for _, row in snap.iterrows()
    }
    return {"values": values}
# Redirect print() to logging.info
class StreamToLogger:
    def __init__(self, level):
        self.level = level
        self.buffer = ""

    def write(self, message):
        for line in message.rstrip().splitlines():
            self.level(line)

    def flush(self):
        pass

sys.stdout = StreamToLogger(logging.info)

with open("config.yaml") as f:
    config = yaml.safe_load(f)
filters = config["filters"]
watchlist_path = config.get("watchlist", "watchlist.txt")
polygon_key = config.get("api_keys", {}).get("polygon")
alpha_key = config.get("api_keys", {}).get("alpha")
has_polygon = bool(polygon_key and polygon_key != "YOUR_API_KEY_HERE")
has_alpha = bool(alpha_key and alpha_key != "YOUR_API_KEY_HERE")
news_limit = config.get("news_limit")

st.set_page_config(layout="wide")
# Inject dark mode theme
dark_mode_css = """
<style>
body {
    background-color: #0E1117 !important;
    color: white !important;
}
[data-testid="stAppViewContainer"] {
    background-color: #0E1117 !important;
}
[data-testid="stSidebar"] {
    background-color: #161B22 !important;
}
</style>
"""
st.markdown(dark_mode_css, unsafe_allow_html=True)
st.title("🌒 Moon Sniper v0.2.1")
st.markdown("[by @ufywufy](https://github.com/ufywufy)", unsafe_allow_html=True)
col1, col2 = st.columns([5, 4])

# RIGHT COLUMN SLIDERS AND STUFF

with col2:
    st.subheader("⚙️ Filters")
    filters_path = "filters.json"
    if "selected_profile" not in st.session_state:
        st.session_state.selected_profile = "(None)"
    if "show_import_filter" not in st.session_state:
        st.session_state["show_import_filter"] = False
    try:
        try:
            with open(filters_path) as f:
                filter_profiles = json.load(f)
        except Exception as e:
            st.warning("⚠️ Could not load filters.json.")
        profile_names = ["(None)"] + list(filter_profiles.keys())
        if "pending_profile_select" in st.session_state:
            p = profile_names.index(st.session_state.pending_profile_select)
            st.session_state.selected_profile = st.selectbox("🎯 Choose Filter Profile", profile_names, index=p)
        else:
            st.session_state.selected_profile = st.selectbox("🎯 Choose Filter Profile", profile_names)
        col_dna1, col_dna2 = st.columns([1, 1])
        with col_dna1:
            if st.button("🧬 Export DNA", key="export_dna_filter"):
                export_dna("filter")
        with col_dna2:
            if st.button("🧬 Import DNA", key="import_dna_filter"):
                st.session_state["show_import_filter"] = True
        if st.session_state.show_import_filter:
            dna_input = st.text_area("Paste DNA filter strings (one per line):", height=150, placeholder="ex: ms:filter,Under the Radar,pc<10,rsit<50,vm<0.7,mcc:1KKK,fc:25KK")
            c1, c2 = st.columns([1, 1])  # Adjust width ratio if needed
            with c1:
                if st.button("💾 Import", key="confirm_import_filter"):
                    st.session_state["show_import_filter"] = False
                    import_dna("filter", dna_input)
                    
            with c2:
                if st.button("❌ Cancel", key="cancel_import_filter"):
                        st.session_state["show_import_filter"] = False
                        st.rerun()
        # Use profile as defaults if selected
        default_vals = filter_profiles[st.session_state.selected_profile] if st.session_state.selected_profile != "(None)" else filters
        # After the selectbox for selected_profile
        if "last_profile" not in st.session_state:
            st.session_state.last_profile = st.session_state.selected_profile

        # Reset state if dropdown changed
        if st.session_state.last_profile != st.session_state.selected_profile:
            for key in ["price_ceiling", "rsi_threshold", "volume_multiplier", "market_cap_ceiling", "float_ceiling"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.last_profile = st.session_state.selected_profile
            unsaved_changes = False  # prevent flag from showing
            st.rerun()  # force refresh to sync inputs

    except Exception as e:
        default_vals = filters

    # Auto generate default name if creating new
    def generate_default_name(existing):
        base = "Profile"
        i = 1
        while f"{base} {i}" in existing:
            i += 1
        return f"{base} {i}"

    pc_col1, pc_col2 = st.columns([3, 1])
    with pc_col1:
        price_c = st.slider("Price Ceiling ($)", 0.5, 1000.0, float(default_vals["price_ceiling"]))
    with pc_col2:
        price_c_input = st.number_input(" ", value=price_c, step=0.5, format="%.2f")
        if price_c_input != price_c:
            price_c = price_c_input

    rsi_col1, rsi_col2 = st.columns([3, 1])
    with rsi_col1:
        rsi_c = st.slider("RSI Threshold", 10, 100, int(default_vals["rsi_threshold"]))
    with rsi_col2:
        rsi_input = st.number_input(" ", min_value=1, max_value=999, value=rsi_c)
        if rsi_input != rsi_c:
            rsi_c = rsi_input

    vol_col1, vol_col2 = st.columns([3, 1])
    with vol_col1:
        vol_mul = st.slider("Volume × avg", 0.0, 10.0, float(default_vals["volume_multiplier"]))
    with vol_col2:
        vol_input = st.number_input(" ", min_value=0.0, value=vol_mul, step=0.1)
        if vol_input != vol_mul:
            vol_mul = vol_input
    pe_col1, pe_col2 = st.columns([3, 1])
    with pe_col1:
        pe_max = st.slider("PE Ratio Max", 0.0, 100.0, float(default_vals.get("pe_max", 20.0)))
    with pe_col2:
        pe_input = st.number_input(" ", value=pe_max, step=0.1)
        if pe_input != pe_max:
            pe_max = pe_input
    eps_col1, eps_col2 = st.columns([3, 1])
    with eps_col1:
        eps_min = st.slider("EPS Minimum", -30.0, 50.0, float(default_vals.get("eps_min", -10.0)))
    with eps_col2:
        eps_input = st.number_input(" ", value=eps_min, step=0.1)
        if eps_input != eps_min:
            eps_min = eps_input
    pct_col1, pct_col2 = st.columns([3, 1])
    with pct_col1:
        pct_min = st.slider("% Change Min", -50.0, 50.0, float(default_vals.get("pct_min", -50.0)))
    with pct_col2:
        pct_input = st.number_input(" ", value=pct_min, step=1.0)
        if pct_input != pct_min:
            pct_min = pct_input



    mc_col, float_col = st.columns(2)
    with mc_col:
        market_cap_c = st.number_input(
            "Market Cap Ceiling", min_value=0.0,
            value=float(default_vals["market_cap_ceiling"]),
            step=100_000.0, format="%.0f"
        )
        st.markdown(f"{market_cap_c:,.0f}", unsafe_allow_html=True)

    with float_col:
        float_c = st.number_input(
            "Float Ceiling", min_value=0.0,
            value=float(default_vals.get("float_ceiling", 0)),
            step=100_000.0, format="%.0f"
        )
        st.markdown(f"{float_c:,.0f}", unsafe_allow_html=True)

    macd_c = default_vals.get("only_positive_macd", False)

    profile_form_col1, profile_form_col2 = st.columns([3, 1])

    # If editing existing profile
    if st.session_state.selected_profile != "(None)":
        profile_name = profile_form_col1.text_input("Profile Name", value=st.session_state.selected_profile)
        save_label = "Save current profile"
    else:
        default_name = generate_default_name(filter_profiles.keys())
        profile_name = profile_form_col1.text_input("Profile Name", value=default_name)
        save_label = "Save as a new profile"

    unsaved_changes = False
    if st.session_state.selected_profile != "(None)":
        saved = filter_profiles[st.session_state.selected_profile]
        current = {
            "price_ceiling": price_c,
            "rsi_threshold": rsi_c,
            "volume_multiplier": vol_mul,
            "market_cap_ceiling": market_cap_c,
            "float_ceiling": float_c,
            "only_positive_macd": macd_c,
            "pe_max": pe_max,
            "eps_min": eps_min,
            "pct_min": pct_min
        }
        for k in current:
            if current[k] != saved.get(k):
                unsaved_changes = True
                break
        if profile_name != st.session_state.selected_profile:
            unsaved_changes = True

    if unsaved_changes:
        st.markdown('<span style="color:orange"><strong>Unsaved profile changes</strong></span>', unsafe_allow_html=True)
    # Save button
    with profile_form_col2:
        if st.button(save_label):
            new_profile = {
                "price_ceiling": price_c,
                "rsi_threshold": rsi_c,
                "volume_multiplier": vol_mul,
                "market_cap_ceiling": market_cap_c,
                "float_ceiling": float_c,
                "only_positive_macd": macd_c,
                "pe_max": pe_max,
                "eps_min": eps_min,
                "pct_min": pct_min

            }

            try:
                # If renaming an existing profile
                if st.session_state.selected_profile != "(None)" and profile_name != st.session_state.selected_profile:
                    filter_profiles.pop(st.session_state.selected_profile, None)

                # Overwrite or add new
                filter_profiles[profile_name] = new_profile

                # Write to JSON
                with open(filters_path, "w") as f:
                    json.dump(filter_profiles, f, indent=2)

                st.success(f"✅ Profile '{profile_name}' saved.")
                st.session_state.pending_profile_select = profile_name
                st.rerun()

            except Exception as e:
                st.error(f"❌ Failed to save profile: {e}")
        if st.session_state.selected_profile != "(None)":
            if st.button("🗑 Delete this profile"):
                try:
                    filter_profiles.pop(st.session_state.selected_profile, None)

                    # Save the updated profiles
                    with open(filters_path, "w") as f:
                        json.dump(filter_profiles, f, indent=2)

                    st.success(f"🗑 Profile '{st.session_state.selected_profile}' deleted.")
                    st.session_state.pending_profile_select = "(None)"
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Failed to delete profile: {e}")




    #sniper picks
    st.subheader("🔫 YAML Picks")
    now = datetime.now().strftime("%b %d, %Y %H:%M")
    st.write(f"_As of **{now}**_")

    picks_placeholder = st.empty()

# LEFT COLUMN BUILD CHART

with col1:
    
    d = WatchlistDf(watchlist_path)
    df = d.build_df()
    _df_for_snapshot = df.copy()
    # apply filters
    view = WatchlistView(df)
    view.apply_filters(price_c, rsi_c, vol_mul, market_cap_c, float_c, macd_c, pe_max, eps_min, pct_min)
    view.format_df()
    check_alerts(view.df, config)
    search = st.text_input("🔎 Search watchlist")
    (df, df_pretty) = view.search(search)

    st.markdown("🔍 Advanced Filter Expression")
    user_filter_expr = st.text_input("Enter expression (ex: RSI < 30 and Price < 5 and MarketCap > 1000000)")
    try:
        (df, df_pretty) = view.expr(user_filter_expr)
    except Exception:
        st.error("Invalid expression")
        

    # reorder picks first
    df_pretty      = pd.concat([view.df_pretty[view.df_pretty["TopPick"]], view.df_pretty[~view.df_pretty["TopPick"]]]).reset_index(drop=True)
    df_pretty = df_pretty.fillna("N/A")
    # session state for selection
    if "sel_ticker" not in st.session_state:
        st.session_state.sel_ticker = df_pretty["Ticker"].iat[0]

    # render grid
    st.subheader("📋 Watchlist (click a row)")
    r = WatchlistGrid(df_pretty)
    grid = r.build_grid(col_state=st.session_state.get("watchlist_col_state"))
    rows = grid.get("selected_rows", []) or []
    if rows:
        last = rows[-1]
        tkr = last.get("Ticker")
        if tkr:
            st.session_state.sel_ticker = tkr

    #top picks button
    top_picks = df[df["TopPick"] == True]["Ticker"].tolist()
    if top_picks:
        if st.button("📄 Export filtered rows to TXT"):
            os.makedirs("output", exist_ok=True)

            # Find next available filename
            base_name = "top_picks"
            existing = os.listdir("output")
            nums = [
                int(match.group(1))
                for f in existing
                if (match := re.match(rf"{base_name}(\d*)\.txt", f)) and match.group(1)
            ]
            next_num = max(nums, default=0) + 1
            filename = f"{base_name}{next_num if next_num > 1 else ''}.txt"
            file_path = os.path.join("output", filename)

            with open(file_path, "w") as f:
                for t in top_picks:
                    f.write(f"{t}\n")

            st.success(f"✅ Exported {len(top_picks)} tickers to {file_path}")
    #Chart
    st.subheader(f"📈 {st.session_state.sel_ticker}")
    if "timeframe" not in st.session_state:
        st.session_state["timeframe"] = "1d"
    timeframe_options = ["1d", "5d", "1mo", "6mo", "YTD", "1y", "5y", "All"]
    timeframe = st.radio(
        "Time Frame",
        timeframe_options,
        index=timeframe_options.index(st.session_state["timeframe"]),
        horizontal=True
    )
    if timeframe != st.session_state.timeframe:
        st.session_state.timeframe = timeframe
        st.rerun()
    if "show_intraday" not in st.session_state:
        st.session_state["show_intraday"] = True
    if "last_tf" not in st.session_state or st.session_state.last_tf != timeframe:
        st.session_state.last_tf = timeframe
        st.session_state.show_intraday = True
    if timeframe in ["1d", "5d"]:
        if has_polygon:
            st.checkbox("🔁 Show Intraday Chart", key="show_intraday")
        else:
            st.checkbox("🔁 Show Intraday Chart", key="show_intraday", disabled=True)
            st.markdown(
                "⚠️ <span style='color:orange'>Add your Polygon API key in config.yaml to enable after-hours charting.</span>",
                unsafe_allow_html=True
            )
        intra = st.session_state["show_intraday"]
    else:
        intra = True
    # Ensure defaults exist (only runs once)
    for key in ("indicator_ema9","indicator_vwap","indicator_bbands"):
        if key not in st.session_state:
            st.session_state[key] = True
    st.markdown("📌 Indicators:")
    col_ema, col_vwap, col_bb = st.columns(3)
    # === Sidebar or wherever you're placing your checkboxes ===
    ema_check = col_ema.checkbox(
        "EMA 9",
        key="indicator_ema9"
    )
    vwap_check = col_vwap.checkbox(
        "VWAP",
        key="indicator_vwap"
    )
    bb_check  = col_bb.checkbox(
        "Bollinger Bands",
        key="indicator_bbands"
    )

    # Now build your dict from session_state
    indicators = {
        "ema9":   st.session_state["indicator_ema9"],
        "vwap":   st.session_state["indicator_vwap"],
        "bbands": st.session_state["indicator_bbands"],
    }
    try:
        ticker = st.session_state.sel_ticker
        hist = yf.Ticker(ticker).history(period=timeframe)

        if not hist.empty:
            if timeframe == "1d":
                # Use previous close if available
                prev_close = yf.Ticker(ticker).info.get("previousClose")
                last_price = hist["Close"].iloc[-1]
                if prev_close:
                    pct_change = round((last_price - prev_close) / prev_close * 100, 2)
                else:
                    pct_change = 0.0
            else:
                start_price = hist["Close"].iloc[0]
                end_price = hist["Close"].iloc[-1]
                pct_change = round((end_price - start_price) / start_price * 100, 2)

            change_color = "green" if pct_change > 0 else "red" if pct_change < 0 else "gray"
            st.markdown(f"**% Change ({timeframe}):** <span style='color:{change_color}'>{pct_change:+.2f}%</span>", unsafe_allow_html=True)

        us_now = datetime.now(pytz.timezone("US/Eastern"))
        if timeframe == "1d" and not intra and us_now.weekday() >= 5:
            st.info("📅 It's the weekend, after hours unavailable.")
        else:
            fig = Chart(ticker, timeframe, intra, polygon_key, indicators=indicators).figure()

            if isinstance(fig, tuple) and fig[0] == "polygon_error":
                code = fig[1]
                if code == 401:
                    st.markdown("❌ <span style='color:red'>Invalid Polygon API key. Please update your config.yaml.</span>", unsafe_allow_html=True)
                elif code == 429:
                    st.markdown("⚠️ <span style='color:orange'>Polygon rate limit exceeded. Try again later or upgrade your plan.</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"❌ <span style='color:red'>Polygon API error: {code}</span>", unsafe_allow_html=True)
            else:
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Could not load chart: {e}")

    # 🧠 AI NEWS
    with st.expander("🧠 Ticker News", expanded=True):
        if has_alpha:
            news = get_news(st.session_state.sel_ticker, limit=news_limit, alpha_api=alpha_key)
            if not news:
                st.info("No news found for this ticker.")
            else:
                def sentiment_color(sentiment):
                    if sentiment == "positive":
                        return "green"
                    elif sentiment == "negative":
                        return "red"
                    else:
                        return "gray"

                for item in news:
                    color = sentiment_color(item["sentiment"].lower())
                    st.markdown(f"""
                <div style="margin-bottom:0.75rem;">
                    <span style="font-size:14px;">
                        📄 <a href="{item['url']}" target="_blank" style="color:#339CFF; text-decoration:none; font-weight:600;">
                        {item['title']}
                        </a><br>
                        <span style="font-size:12px;">
                            <span style="color:gray;">🕒 {item['timestamp']}</span>
                            Sentiment: <span style="color:{color}; font-weight:500;">{item['sentiment'].lower()}</span>
                            Confidence: <span style="color:{color}; font-weight:500;">{item['confidence']}</span>
                        </span>
                    </span>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.markdown(
                "⚠️ <span style='color:orange'>Add your AlphaVantage API key in config.yaml to enable news</span>",
                unsafe_allow_html=True
            )


    # —— Auto-Refresh Interval ——
    st.markdown("#### Auto-Refresh Interval")
    c1, c2, c3 = st.columns([1, 1, 2])

    if "auto_hours" not in st.session_state:
        st.session_state.auto_hours = filters.get("refresh_hours", 0)
    if "auto_minutes" not in st.session_state:
        st.session_state.auto_minutes = filters.get("refresh_mins", 5)

    hrs = c1.number_input("Hours", 0, 24, key="auto_hours")
    mns = c2.number_input("Minutes", 0, 59, key="auto_minutes")

    total_secs = int(hrs) * 3600 + int(mns) * 60
    if total_secs <= 0:
        c3.write("**Next refresh:** (auto-refresh off)")
        refresh_count = st.session_state.get("refresh_counter")  # do not trigger
    else:
        interval_ms = max(total_secs * 1000, 1000)  # floor at 1s to prevent thrash
        next_run = datetime.now() + timedelta(seconds=total_secs)
        c3.write(f"**Next refresh:** {next_run.strftime('%b %d, %Y %H:%M:%S')}")
    refresh_count = st_autorefresh(interval=interval_ms, limit=None, key="refresh_counter")
    last_count = st.session_state.get("last_refresh_counter")
    if refresh_count != last_count and total_secs > 0:
        st.session_state["refresh_snapshot"] = _moves_snapshot(_df_for_snapshot)
        st.session_state["last_refresh_counter"] = refresh_count


with col2:
    picks = YamlPicks(filters, df).get()
    if picks:
        for ticker, reasons in picks.items():
            st.markdown(f"<span style='color:gold'><strong>{ticker}</strong>: {reasons}</span>", unsafe_allow_html=True)
    else:
        st.write("_No picks under YAML filters._")
    show_alert_modal(view, config, d.wl)