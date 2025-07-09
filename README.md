# 🌒 Moon Sniper

Moon Sniper is a completely FREE, open source stock screener and alerting platform you can run locally. Powered by Python + Streamlit. Upload your own `.txt` watchlists and unlock a plethora of awesome tools most platforms hide behind subscriptions:

## 🔫 Features

- Interactive table with 9 key stat columns (Price, RSI, Avg Vol, Market Cap, Float, etc.)
- Dynamic filtering, ascending/descending rows, sliders, values
- Custom filter profiles (ex: breakout, dip catcher, moon sniper, safe growth)
- Export filtered tickers as a txt file
- Advanced filter expression (ex: RSI < 30 and Price > 40)
- Charts across all timeframes + after hours + volume bars, refreshes every 5 mins
- Unlimited custom alerts with filter logic via emails, webhooks or desktop. No expiration, no limits.
- DNA codes for profiles and alerts, share and import setups with a click!

All you need is Python, then run `setup.bat` and `main.bat`

Coming soon:
Batch csvs + graphs + formatted datasets to plug and play into ML models
Historical analysis
Advanced chart indicators, custom chart indicators, smart heuristic summaries
AI powered 👀

## 🛠️ Getting Started

1. Install Requirements
Install Python
Run `setup.bat` which downloads all the requirements
Or navigate to app/ and run `pip install -r requirements.txt`

3. Setup Config
Fill out config.yaml, you can open this as a `.txt` file
Add watchlists as `.txt` files (1 ticker per line) inside the watchlists/ folder

4. Launch Streamlit UI
Run `main.bat`
This opens your local web UI where you do everything

5. Start the Alerts Daemon (Optional)
If you don't have the UI open, you can run `alerts.bat` which will run your alerts in the background

## 🔢 Expression Syntax

Expressions are mathematical and intuitive, used by both advanced filtering and the alerts
ex: RSI > 70 and AvgVolume > 1000000
Price < 10 and MACD > 0

## 📧 Alerts

Desktop (local notifications)
Email (via Brevo)
Webhooks (like Discord)

Fully custom
Persistent
No duplicates (triggered alerts auto-remove or mark)

## 🧬 DNA (Import/Export)

Export filters/alerts into readable DNA codes
ex: `ms:filter,a_cool_name,pc<1000,rsit<60,vm<0.5,mcc:100KK,fc:1KK,MACD:true`
Share or import setups easily through the UI

## ⚠️ Disclaimer

Moon Sniper is alpha-stage software. This was built fast, ugly, but functional. Expect bugs. Expect weirdness. But it’s free forever, and it will evolve.

## 🤝 Community

Ideas? Feedback? Need help? Just wanna vibe?
Whether you're a beginner or a seasoned sniper, reach out, open an issue, or submit a pull request (please)

https://discord.gg/E6x2wFzCtX

Happy sniping.

ufywfuy

## License

MIT
