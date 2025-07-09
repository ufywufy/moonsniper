import json
import os
import re
import streamlit as st

# Path to JSON files
FILTERS_FILE = os.path.join(os.path.dirname(__file__), "..", "filters.json")
ALERTS_FILE = os.path.join(os.path.dirname(__file__), "..", "alerts", "alerts.json")
FILTERS_FILE = os.path.abspath(FILTERS_FILE)
ALERTS_FILE = os.path.abspath(ALERTS_FILE)

FILTER_PATTERN = re.compile(
    r"^ms:filter,([^,]+),pc<([\d\.]+),rsit<([\d\.]+),vm<([\d\.]+),mcc:([\dK]+),fc:([\dK]+)(,MACD:(True|False))?$"
)
ALERT_PATTERN = re.compile(
    r"^ms:alert,([^,]+),([^,]+),([^,]+),message:(.+)$"
)

def export_dna(data_type):
    dna_strings = []
    if data_type == "filter":
        if not os.path.exists(FILTERS_FILE):
            st.error("Cannot find filter path")
            return
        with open(FILTERS_FILE, "r") as f:
            filters = json.load(f)
        for name, profile in filters.items():
            parts = ["ms:filter", name]
            if "price_ceiling" in profile:
                parts.append(f"pc<{int(profile["price_ceiling"])}")
            if "rsi_threshold" in profile:
                parts.append(f"rsit<{int(profile["rsi_threshold"])}")
            if "volume_multiplier" in profile:
                parts.append(f"vm<{float(profile["volume_multiplier"])}")
            if "market_cap_ceiling" in profile:
                mcc = int(profile["market_cap_ceiling"])
                parts.append(f"mcc:{format_big(mcc)}")
            if "float_ceiling" in profile:
                fc = int(profile["float_ceiling"])
                parts.append(f"fc:{format_big(fc)}")
            if "macd_enabled" in profile:
                parts.append(f"MACD:{str(profile["macd_enabled"])}")
            dna_strings.append(",".join(parts))
            print(dna_strings)

    elif data_type == "alert":
        if not os.path.exists(ALERTS_FILE):
            st.error("Cannot find alert path")
            return
        with open(ALERTS_FILE, "r") as f:
            alerts_data = json.load(f)
        for ticker, alerts in alerts_data.get("tickers", {}).items():
            for a in alerts:
                parts = ["ms:alert", ticker, a["expression"], a["channel"]]
                parts.append(f"message:{a["message"]}")
                dna_strings.append(",".join(parts))
        for a in alerts_data.get("scanners", []):
            parts = ["ms:alert", "*", a["expression"], a["channel"]]
            parts.append(f"message:{a["message"]}")
            dna_strings.append(",".join(parts))

    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    # Write to file inside /output/
    file_path = os.path.join("output", f"dna_{data_type}.txt")
    with open(file_path, "w") as f:
        f.write("\n".join(dna_strings))
    st.success(f"✅ Exported {len(dna_strings)} {data_type} DNA lines -> {file_path}")
    print(f"[Exported] {len(dna_strings)} {data_type} DNA lines -> {file_path}")



def import_dna(data_type, dna_text):
    lines = [line.strip() for line in dna_text.splitlines() if line.strip()]
    errors = []
    if data_type == "filter":
        if os.path.exists(FILTERS_FILE):
            with open(FILTERS_FILE, "r") as f:
                filters = json.load(f)
            if not isinstance(filters, dict):
                filters = {p["name"]: p for p in filters if "name" in p}
        else:
            filters = {}

        for line in lines:
            if not FILTER_PATTERN.match(line):
                errors.append(f"Invalid filter DNA format: {line}")
                continue
            parts = line.split(",")
            name = parts[1]
            profile = {"name": name}
            for token in parts[2:]:
                if token.startswith("pc<"):
                    profile["price_ceiling"] = float(token[3:])
                elif token.startswith("rsit<"):
                    profile["rsi_threshold"] = float(token[5:])
                elif token.startswith("vm<"):
                    profile["volume_multiplier"] = float(token[3:])
                elif token.startswith("mcc:"):
                    profile["market_cap_ceiling"] = parse_big(token[4:])
                elif token.startswith("fc:"):
                    profile["float_ceiling"] = parse_big(token[3:])
                elif token.startswith("MACD:"):
                    profile["macd_enabled"] = token[5:].lower() == "true"
            filters[name] = profile

        with open(FILTERS_FILE, "w") as f:
            json.dump(filters, f, indent=4)

    elif data_type == "alert":
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, "r") as f:
                alerts_data = json.load(f)
        else:
            alerts_data = {"tickers": {}, "scanners": []}

        for line in lines:
            if not ALERT_PATTERN.match(line):
                errors.append(f"Invalid alert DNA format: {line}")
                continue
            # Parse alert line
            parts = line.split(",")
            ticker = parts[1]
            expression = parts[2]
            channel = parts[3]
            message = parts[4][len("message:"):]
            alert_obj = {
                "expression": expression,
                "channel": channel,
                "message": message
            }
            if ticker == "*":
                alerts_data["scanners"].append(alert_obj)
            else:
                if ticker not in alerts_data["tickers"]:
                    alerts_data["tickers"][ticker] = []
                alerts_data["tickers"][ticker].append(alert_obj)

        with open(ALERTS_FILE, "w") as f:
            json.dump(alerts_data, f, indent=4)

    if errors:
        st.error("Some lines were invalid and skipped:\n" + "\n".join(errors))
    else:
        st.success("Import good")
        st.rerun()


def format_big(n):
    n = int(n)
    if n % 1_000_000_000 == 0 and n >= 1_000_000_000:
        return f"{n // 1_000_000_000}KKK"
    elif n % 1_000_000 == 0 and n >= 1_000_000:
        return f"{n // 1_000_000}KK"
    elif n % 1_000 == 0 and n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


def parse_big(s):
    if s.endswith("KKK"):
        return int(s[:-3]) * 1_000_000_000
    elif s.endswith("KK"):
        return int(s[:-2]) * 1_000_000
    elif s.endswith("K"):
        return int(s[:-1]) * 1_000
    return int(s)