import streamlit as st
st.set_page_config(layout="wide")
st.title('here')

import pandas as pd
import panel as pn
import io
from backtester import BackTester
from data_manager import fetch_data

pn.extension('plotly', 'tabulator')


st.title("Backtesting Dashboard")

df = fetch_data("BTC-USD", "2025-08-01", "2025-10-05", period="1h")
df.columns = df.columns.get_level_values(0)

st.write(df.head())

# Example dummy signals
def entry_long(prev, curr): 
    return curr["Close"] > prev["High"]

def exit_long(prev, curr): 
    return curr["Close"] < prev["Low"]

def entry_short(prev, curr): 
    return curr["Close"] < prev["Low"]

def exit_short(prev, curr): 
    return curr["Close"] > prev["High"]

bt = BackTester(df, slippage=10,cooling_period=2)
trades = bt.run_backtest(entry_long, exit_long, entry_short, exit_short)
st.write('backtest.run')

#print(trades)
dashboard = bt.panel_dashboard()

html_io = io.StringIO()
dashboard.save(html_io, embed=True)  # full HTML with JS and CSS
html = html_io.getvalue()

st.components.v1.html(html, height=1000, scrolling=True)
