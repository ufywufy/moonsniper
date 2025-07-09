from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
class WatchlistGrid:

    def __init__(self, df_pretty):
        self.df = df_pretty
        
    def build_grid(self):

            gb = GridOptionsBuilder.from_dataframe(self.df)
            gb.configure_selection("single", use_checkbox=False)
            gb.configure_column("TopPick", hide=True)

            for c in self.df.columns:
                gb.configure_column(c, cellStyle=JsCode("""
                    function(params) {
                        if (params.data.TopPick) {
                            return {"backgroundColor":"#800000","color":"white"};
                        }
                        return null;
                    }
                    """))

            # Formatter: always show 2 decimal places with thousands separator
            for col in ["Price", "RSI", "MACD", "Volume", "Avg Vol", "Float", "Market Cap"]:
                gb.configure_column(
                    col,
                    type=["numericColumn", "rightAligned"],
                    valueFormatter=JsCode("""
                    function(params) {
                        return params.value.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                    }
                    """)
                )
            # Special formatting for Market Cap with $
            gb.configure_column(
                "Market Cap",
                type=["numericColumn", "rightAligned"],
                valueFormatter=JsCode("""
                function(params) {
                    return "$" + params.value.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                }
                """)
            )
            gb.configure_grid_options(rowHeight=35)
            return AgGrid(
                self.df,
                gridOptions=gb.build(),
                height=300,
                fit_columns_on_grid_load=True,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                allow_unsafe_jscode=True,
                enable_enterprise_modules=True
            )