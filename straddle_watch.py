import streamlit as st
import requests
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Straddle Watch", layout="wide")

st.title("📊 Straddle Watch - India Options")
st.write("Get CE/PE prices, IV, OI, events, and an automated BUY/AVOID straddle suggestion.")

# -------------------- USER INPUTS --------------------
symbol = st.text_input("Enter Stock/Index (e.g. BANKNIFTY, NIFTY, RELIANCE)", "BANKNIFTY")
strike_price = st.number_input("Enter Strike Price (e.g. 49000 for BankNifty)", value=49000)
expiry_date = st.text_input("Enter Expiry Date (e.g. 07-Aug-2025)", "07-Aug-2025")

# -------------------- NSE Option Chain --------------------
def get_option_chain(symbol):
    if symbol in ["NIFTY", "BANKNIFTY"]:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    else:
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    r = session.get(url, headers=headers)
    if r.status_code != 200:
        return None
    return r.json()

# -------------------- NSE Corporate Events --------------------
def get_corporate_events():
    url = "https://www.nseindia.com/api/corporate-announcements?index=equities"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    r = session.get(url, headers=headers)
    if r.status_code != 200:
        return []
    return r.json().get('announcements', [])

# -------------------- Global Cues --------------------
def get_global_cues():
    cues = {}
    try:
        cues['Dow Futures'] = yf.Ticker("^DJI").info.get("regularMarketPrice", "N/A")
        cues['SGX Nifty'] = yf.Ticker("^NSEI").info.get("regularMarketPrice", "N/A")
        cues['Crude Oil'] = yf.Ticker("CL=F").info.get("regularMarketPrice", "N/A")
        cues['USD-INR'] = yf.Ticker("USDINR=X").info.get("regularMarketPrice", "N/A")
    except:
        cues = {"Dow Futures": "N/A", "SGX Nifty": "N/A", "Crude Oil": "N/A", "USD-INR": "N/A"}
    return cues

st.subheader("📈 Option Chain Analysis")

# --- Fetch Option Chain ---
oc_data = get_option_chain(symbol)
decision = "❌ Cannot fetch option chain (weekend or blocked)"

if oc_data:
    df = pd.DataFrame(oc_data['records']['data'])
    df = df[df['expiryDate'] == expiry_date]
    atm_data = df[df['strikePrice'] == strike_price]

    if not atm_data.empty:
        ce_price = atm_data['CE'].iloc[0]['lastPrice']
        pe_price = atm_data['PE'].iloc[0]['lastPrice']
        ce_iv = atm_data['CE'].iloc[0]['impliedVolatility']
        pe_iv = atm_data['PE'].iloc[0]['impliedVolatility']
        ce_oi = atm_data['CE'].iloc[0]['openInterest']
        pe_oi = atm_data['PE'].iloc[0]['openInterest']

        st.write(f"**CE Price:** ₹{ce_price} | **PE Price:** ₹{pe_price}")
        st.write(f"**IV:** { (ce_iv+pe_iv)/2 :.2f}% | **CE OI:** {ce_oi} | **PE OI:** {pe_oi}")

        avg_iv = (ce_iv + pe_iv) / 2
        total_premium = ce_price + pe_price

        # --- Event Check ---
        events = get_corporate_events()
        event_flag = False
        for e in events[:50]:
            if any(word in e['desc'] for word in ["Result", "Meeting", "Dividend"]):
                if symbol in e['symbol']:
                    event_flag = True
                    st.write(f"📜 Event: {e['symbol']} → {e['desc']} on {e['dt']}")

        # --- Decision Logic ---
        if avg_iv < 25 and event_flag:
            decision = "✅ **BUY STRADDLE** (Low IV + Event Trigger)"
        elif avg_iv > 50 and event_flag:
            decision = "⚠️ **RISKY STRADDLE** (IV too high, only if expecting big gap)"
        elif avg_iv < 25 and not event_flag:
            decision = "📈 **Possible Straddle** (Low IV but no major event)"
        else:
            decision = "❌ **AVOID STRADDLE** (High IV & No trigger)"

st.subheader("🌍 Global Market Cues")
cues = get_global_cues()
st.write(cues)

st.subheader("🎯 Decision")
st.markdown(f"### {decision}")
