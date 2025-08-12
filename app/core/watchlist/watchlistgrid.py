from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import streamlit as st

class WatchlistGrid:
    def __init__(self, df_pretty):
        self.df = df_pretty

    def build_grid(self, col_state=None):
        gb = GridOptionsBuilder.from_dataframe(self.df)
        gb.configure_selection("single", use_checkbox=False)
        gb.configure_column("TopPick", hide=True)

        # Row highlight for TopPick
        for c in self.df.columns:
            gb.configure_column(c, cellStyle=JsCode("""
                function(params) {
                    if (params.data.TopPick) {
                        return {"backgroundColor":"#800000","color":"white"};
                    }
                    return null;
                }
            """))

        # Format numeric columns
        format_cols = [
            "Price","RSI","MACD","Volume","Avg Vol",
            "Float","Market Cap","PE Ratio","EPS","Pct Change",
            "priceMove","volMove","rsiMove"
        ]

        for col in format_cols:
            if col in self.df.columns:
                formatter = JsCode("""
                    function(params) {
                        if (params.value == null) return "";
                        var v = Number(params.value);
                        var opts = {minimumFractionDigits: 2, maximumFractionDigits: 2};
                        var f = params.colDef.field;

                        if (f === "Market Cap") {
                            return "$" + v.toLocaleString(undefined, opts);
                        }
                        if (f === "priceMove" || f === "volMove" || f === "Pct Change") {
                            return v.toLocaleString(undefined, opts) + "%";
                        }
                        return v.toLocaleString(undefined, opts);
                    }
                """)
                gb.configure_column(col, type=["numericColumn","rightAligned"], valueFormatter=formatter)

        # Show Columns tool panel; apply saved column state if we have it
        
        go = gb.build()

        # apply saved state if present; else hide TopPick by default
        saved = st.session_state.get("watchlist_col_state")
        go["columnState"] = saved or [{"colId": "TopPick", "hide": True}]

        resp = AgGrid(
            self.df,
            gridOptions=go,
            height=400,
            fit_columns_on_grid_load=True,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            allow_unsafe_jscode=True,
            enable_enterprise_modules=True,
            key="watchlist_grid",
        )

        # persist latest column state (so if user shows TopPick, it sticks)
        if resp:
            state = resp.get("column_state") or (resp.get("grid_state", {}) or {}).get("columnState")
            if state:
                st.session_state["watchlist_col_state"] = state

        return resp
