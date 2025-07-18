import pandas as pd

class YamlPicks:
    def __init__(self, filters, df):
        self.filters = filters
        self.df = df

    def get(self):
        # pull original filter values from config.yaml
        price_ceiling   = float(self.filters["price_ceiling"])
        rsi_threshold   = float(self.filters["rsi_threshold"])
        volume_multiplier = float(self.filters["volume_multiplier"])
        market_cap_ceiling = float(self.filters["market_cap_ceiling"])
        float_ceiling   = float(self.filters.get("float_ceiling", 0))
        macd_enabled    = self.filters.get("only_positive_macd", False)
        min_pct_change  = self.filters.get("min_pct_change", None)
        max_pct_change  = self.filters.get("max_pct_change", None)
        max_pe_ratio    = self.filters.get("max_pe_ratio", None)

        # base filter
        cond = (
            (self.df["Price"] <= price_ceiling) &
            (self.df["RSI"] <= rsi_threshold) &
            (self.df["Volume"] > volume_multiplier * self.df["Avg Vol"]) &
            (self.df["Market Cap"] <= market_cap_ceiling) &
            ((self.df["Float"].isna()) | (self.df["Float"] <= float_ceiling))
        )

        # optional filters
        if macd_enabled:
            cond &= self.df["MACD"] > 0
        if min_pct_change is not None:
            cond &= self.df["Pct Change"] >= float(min_pct_change)
        if max_pct_change is not None:
            cond &= self.df["Pct Change"] <= float(max_pct_change)
        if max_pe_ratio is not None:
            cond &= (self.df["PE Ratio"].isna() | (self.df["PE Ratio"] <= float(max_pe_ratio)))

        df_picks = self.df[cond]
        result = {}

        for _, row in df_picks.iterrows():
            reasons = []
            if row["Price"] <= price_ceiling:
                reasons.append(f"Price {row['Price']:.2f}≤{price_ceiling}")
            if row["RSI"] <= rsi_threshold:
                reasons.append(f"RSI {row['RSI']:.1f}≤{rsi_threshold}")
            if row["Volume"] > volume_multiplier * row["Avg Vol"]:
                reasons.append("Vol spike")
            if row["Market Cap"] <= market_cap_ceiling:
                reasons.append(f"MCap≤{market_cap_ceiling:,}")
            if pd.notna(row["Float"]) and row["Float"] <= float_ceiling:
                reasons.append(f"Float≤{float_ceiling:,}")
            if macd_enabled and row["MACD"] > 0:
                reasons.append("MACD+")
            if min_pct_change is not None and row["Pct Change"] >= min_pct_change:
                reasons.append(f"Pct+{row['Pct Change']:.1f}")
            if max_pct_change is not None and row["Pct Change"] <= max_pct_change:
                reasons.append(f"Pct≤{max_pct_change}")
            if max_pe_ratio is not None and (pd.isna(row["PE Ratio"]) or row["PE Ratio"] <= max_pe_ratio):
                reasons.append(f"PE≤{max_pe_ratio}")

            result[row["Ticker"]] = "; ".join(reasons)

        return result
