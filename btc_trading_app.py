"""
BTC Trading Strategy Dashboard - Streamlit Web App
Fetches pre-computed backtest results directly from GitHub.
This ensures fresh data on every refresh without needing to redeploy.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import requests
import time
from datetime import datetime, timedelta
from io import StringIO
import pytz

# ============================================================
# CONFIGURATION - UPDATE THESE WITH YOUR GITHUB DETAILS
# ============================================================
GITHUB_USERNAME = "ha0zh"
GITHUB_REPO = "btc-db-v3-cron"
GITHUB_BRANCH = "main"
# ============================================================

# Construct raw GitHub URLs
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{GITHUB_BRANCH}"

# Timezone for display
GMT8 = pytz.timezone('Asia/Singapore')

def convert_utc_to_gmt8(utc_str):
    """Convert UTC timestamp string to GMT+8"""
    if not utc_str or utc_str == 'Unknown':
        return utc_str
    try:
        # Parse UTC timestamp (format: "2026-01-11 13:02:26 UTC")
        utc_str_clean = utc_str.replace(' UTC', '')
        utc_dt = datetime.strptime(utc_str_clean, '%Y-%m-%d %H:%M:%S')
        utc_dt = pytz.UTC.localize(utc_dt)
        gmt8_dt = utc_dt.astimezone(GMT8)
        return gmt8_dt.strftime('%Y-%m-%d %H:%M:%S GMT+8')
    except Exception:
        return utc_str

# Page configuration
st.set_page_config(
    page_title="BTC Trading Strategy Dashboard (Cronjob)",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stDataFrame { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📈 BTC Trading Strategy Dashboard (Cronjob)")
st.markdown("**Asian Hours Strategy Backtest & Live Signals**")

# ===== REFRESH BUTTON =====
col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    refresh_clicked = st.button("🔄 Refresh Data", type="primary")
with col2:
    show_debug = st.checkbox("Show debug", value=False)

# Current timestamp for display
load_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"Page loaded: {load_time}")

if refresh_clicked:
    st.rerun()

# ===== FETCH FUNCTIONS (NO CACHING) =====
def fetch_from_github(filepath):
    """
    Fetch a file from GitHub raw URL with cache-busting.
    Returns (content, status_message)
    """
    # Cache-busting: add timestamp to URL
    cache_buster = int(time.time() * 1000)
    url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{GITHUB_BRANCH}/{filepath}?cb={cache_buster}"
    
    headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text, f"✓ Fetched {filepath} ({len(response.text)} bytes)"
        else:
            return None, f"✗ HTTP {response.status_code} for {filepath}"
    except Exception as e:
        return None, f"✗ Error fetching {filepath}: {str(e)}"

def load_results():
    """Load pre-computed backtest results from GitHub - NO CACHING"""
    results = {
        'metrics': {},
        'live_position': None,
        'equity_curve': [],
        'equity_curve_ts': pd.DataFrame(),
        'last_updated': 'Unknown',
        'data_timestamp': 'Unknown',
        'trade_log': pd.DataFrame(),
        'conditions': pd.DataFrame(),
        'indicators': pd.DataFrame(),
        'debug_messages': []
    }
    
    # Load metrics JSON
    metrics_text, msg = fetch_from_github("backtest_results/metrics.json")
    results['debug_messages'].append(msg)
    
    if metrics_text:
        try:
            data = json.loads(metrics_text)
            results['metrics'] = data.get('metrics', {})
            results['live_position'] = data.get('live_position')
            results['equity_curve'] = data.get('equity_curve', [])
            results['last_updated'] = data.get('last_updated', 'Unknown')
            results['data_timestamp'] = data.get('data_latest_timestamp', 'Unknown')
            results['debug_messages'].append(f"  → Backtest timestamp: {results['last_updated']}")
        except Exception as e:
            results['debug_messages'].append(f"  → JSON parse error: {e}")
    
    # Load trade log
    trade_text, msg = fetch_from_github("backtest_results/trade_log.csv")
    results['debug_messages'].append(msg)
    if trade_text:
        try:
            results['trade_log'] = pd.read_csv(StringIO(trade_text))
            results['debug_messages'].append(f"  → {len(results['trade_log'])} trades loaded")
        except Exception as e:
            results['debug_messages'].append(f"  → CSV parse error: {e}")
    
    # Load conditions
    conditions_text, msg = fetch_from_github("backtest_results/conditions.csv")
    results['debug_messages'].append(msg)
    if conditions_text:
        try:
            results['conditions'] = pd.read_csv(StringIO(conditions_text), index_col=0)
        except:
            pass
    
    # Load indicators
    indicators_text, msg = fetch_from_github("backtest_results/indicators.csv")
    results['debug_messages'].append(msg)
    if indicators_text:
        try:
            results['indicators'] = pd.read_csv(StringIO(indicators_text), index_col=0)
        except:
            pass

    # Load time-based equity curve
    equity_ts_text, msg = fetch_from_github("backtest_results/equity_curve_ts.csv")
    results['debug_messages'].append(msg)
    if equity_ts_text:
        try:
            results['equity_curve_ts'] = pd.read_csv(StringIO(equity_ts_text))
            results['debug_messages'].append(f"  → {len(results['equity_curve_ts'])} equity points loaded")
        except Exception as e:
            results['debug_messages'].append(f"  → Equity curve CSV parse error: {e}")

    return results

# ===== LOAD DATA =====
results = load_results()
metrics = results['metrics']
live_position = results['live_position']
trade_log = results['trade_log']
conditions = results['conditions']
indicators = results['indicators']
equity_curve = results['equity_curve']
equity_curve_ts = results['equity_curve_ts']

# ===== DEBUG INFO =====
if show_debug:
    st.markdown("### 🔧 Debug Info")
    st.markdown(f"**GitHub URL base:** `https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{GITHUB_BRANCH}/`")
    st.markdown("**Fetch log:**")
    for msg in results['debug_messages']:
        st.text(msg)
    st.markdown("---")

# ===== HEADER INFO =====
last_run_gmt8 = convert_utc_to_gmt8(results['last_updated'])
st.markdown(f"""
**🕐 Backtest Last Run:** {last_run_gmt8}
**📊 Data Until:** {results['data_timestamp']}
""")
st.markdown("---")

# ===== CHECK IF DATA EXISTS =====
if not metrics:
    st.error("⚠️ Could not load backtest results from GitHub.")
    
    # Show debug by default when there's an error
    st.markdown("### 🔧 Debug Info")
    st.markdown(f"**GitHub URL base:** `https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{GITHUB_BRANCH}/`")
    st.markdown("**Fetch log:**")
    for msg in results['debug_messages']:
        st.text(msg)
    
    st.warning(f"""
    **Please check:**
    1. Update `GITHUB_USERNAME` and `GITHUB_REPO` at the top of `btc_trading_app.py`
    2. Make sure the `backtest_results/` folder exists in your repo
    3. Run the GitHub Actions workflow at least once
    
    **Current configuration:**
    - Username: `{GITHUB_USERNAME}`
    - Repo: `{GITHUB_REPO}`
    """)
    st.stop()

# ===== KEY METRICS =====
st.subheader("📊 Strategy Metrics Summary")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Trades", f"{metrics.get('Trades', 0):,}")
with col2:
    st.metric("Win Rate", f"{metrics.get('Win_rate_pct', 0):.0f}%")
with col3:
    st.metric("Cumulative Return", f"{metrics.get('Cum_return_pct', 0):,.0f}%")
with col4:
    st.metric("Max Drawdown", f"{metrics.get('Max_DD_pct', 0):.0f}%")

# Full metrics table
metrics_display = {
    "Variant": metrics.get('Variant', ''),
    "Capital Risked": metrics.get('Capital_Risked', ''),
    "Trades": metrics.get('Trades', 0),
    "Win-rate %": metrics.get('Win_rate_pct', 0),
    "Win/Loss ratio": metrics.get('Win_Loss_ratio', 0),
    "Cum return %": metrics.get('Cum_return_pct', 0),
    "Max DD %": metrics.get('Max_DD_pct', 0),
    "Max consec losses": metrics.get('Max_consec_losses', 0),
    "Max consec wins": metrics.get('Max_consec_wins', 0),
    "Win-rate 7d %": metrics.get('Win_rate_7d_pct', 0),
    "Trades 7d": metrics.get('Trades_7d', 0),
    "PnL 7d": f"${metrics.get('PnL_7d', 0):,.0f}",
    "Win-rate 30d %": metrics.get('Win_rate_30d_pct', 0),
    "Trades 30d": metrics.get('Trades_30d', 0),
    "PnL 30d": f"${metrics.get('PnL_30d', 0):,.0f}",
}
metrics_df = pd.DataFrame([metrics_display])
st.dataframe(metrics_df, use_container_width=True, hide_index=True)

# ===== LIVE POSITIONS =====
st.markdown("---")
st.subheader("🔴 LIVE POSITIONS")

if live_position:
    live_df = pd.DataFrame([live_position])
    st.dataframe(live_df, use_container_width=True, hide_index=True)
    
    if live_position["position"] == "long":
        st.success(f"📈 **LONG** position open at ${live_position['entry_price']:,.0f}")
    else:
        st.error(f"📉 **SHORT** position open at ${live_position['entry_price']:,.0f}")
    
    st.info(f"Stop: ${live_position['stop_price']:,.0f} | Target: ${live_position['tp_price']:,.0f}")
else:
    st.info("No live position open.")

# ===== SIGNAL CONDITIONS =====
st.markdown("---")
st.subheader("🎯 Signal Conditions (Last 12 Hours)")

if not conditions.empty:
    # Sort by index (timestamp) in descending order - latest first
    conditions_sorted = conditions.sort_index(ascending=False)
    st.dataframe(conditions_sorted, use_container_width=True)
else:
    st.warning("No conditions data available.")

# ===== TECHNICAL INDICATORS =====
st.markdown("---")
st.subheader("📈 Technical Indicators (Last 12 Hours)")

if not indicators.empty:
    # Sort by index (timestamp) in descending order - latest first
    indicators_sorted = indicators.sort_index(ascending=False)
    st.dataframe(indicators_sorted, use_container_width=True)
else:
    st.warning("No indicators data available.")

# ===== TRADE LOG =====
st.markdown("---")
st.subheader("📝 Trade Log (Last 59 Trades)")

if not trade_log.empty:
    # Sort by exit_time in descending order - latest first
    display_df = trade_log.copy()
    if 'exit_time' in display_df.columns:
        display_df = display_df.sort_values('exit_time', ascending=False)

    # Format numeric columns
    for col in ['entry_price', 'stop', 'target', 'exit_price', 'pnl']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f'{x:,.0f}' if pd.notna(x) else '')

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=600)
    
    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Displayed Trades", len(trade_log))
    with col2:
        total_pnl = trade_log['pnl'].sum() if 'pnl' in trade_log.columns else 0
        st.metric("Total PnL (displayed)", f"${total_pnl:,.0f}")
    with col3:
        avg_pnl = trade_log['pnl'].mean() if 'pnl' in trade_log.columns else 0
        st.metric("Avg PnL/Trade", f"${avg_pnl:,.0f}")
else:
    st.warning("No trade log data available.")

# ===== EQUITY CURVE (Trade Number) =====
st.markdown("---")
st.subheader("📈 Equity Curve (by Trade #)")

if equity_curve:
    eq_df = pd.DataFrame({
        'Trade #': range(1, len(equity_curve) + 1),
        'Equity': equity_curve
    })
    st.line_chart(eq_df.set_index('Trade #'))
else:
    st.info("No equity curve data available.")

# ===== EQUITY CURVE (Time-Based) =====
st.markdown("---")
st.subheader("📈 Equity Curve (Time-Based)")

if not equity_curve_ts.empty:
    # Convert exit_time to datetime and to GMT+8
    eq_ts_df = equity_curve_ts.copy()
    eq_ts_df['exit_time'] = pd.to_datetime(eq_ts_df['exit_time'])

    # The data is in UTC, convert to GMT+8
    eq_ts_df['exit_time_gmt8'] = eq_ts_df['exit_time'] + pd.Timedelta(hours=8)

    # Filter controls
    col1, col2 = st.columns(2)

    with col1:
        duration_options = {
            'Last Month': 30,
            'Last 3 Months': 90,
            'Last 6 Months (Default)': 180,
            'Last 1 Year': 365,
            'All Time': 0
        }
        selected_duration = st.selectbox(
            'Duration',
            list(duration_options.keys()),
            index=2  # Default to 6 months
        )
        days_filter = duration_options[selected_duration]

    with col2:
        interval_options = ['Hourly', 'Daily']
        selected_interval = st.selectbox(
            'Interval',
            interval_options,
            index=0  # Default to Hourly
        )

    # Apply duration filter
    if days_filter > 0:
        latest_date = eq_ts_df['exit_time_gmt8'].max()
        cutoff_date = latest_date - pd.Timedelta(days=days_filter)
        eq_ts_filtered = eq_ts_df[eq_ts_df['exit_time_gmt8'] >= cutoff_date].copy()
    else:
        eq_ts_filtered = eq_ts_df.copy()

    if not eq_ts_filtered.empty:
        # Resample based on interval selection
        eq_ts_filtered = eq_ts_filtered.set_index('exit_time_gmt8')

        if selected_interval == 'Daily':
            # Take the last equity value for each day
            eq_resampled = eq_ts_filtered['equity'].resample('D').last().dropna()
        else:
            # Hourly: take the last equity value for each hour
            eq_resampled = eq_ts_filtered['equity'].resample('h').last().dropna()

        if not eq_resampled.empty:
            # Format the index for display
            chart_df = pd.DataFrame({
                'Equity': eq_resampled.values
            }, index=eq_resampled.index)

            st.line_chart(chart_df)

            # Show date range info
            start_date = eq_resampled.index.min().strftime('%Y-%m-%d %H:%M')
            end_date = eq_resampled.index.max().strftime('%Y-%m-%d %H:%M')
            st.caption(f"Showing {len(eq_resampled)} data points from {start_date} to {end_date} (GMT+8)")
        else:
            st.info("No data available for the selected filters.")
    else:
        st.info("No data available for the selected duration.")
else:
    st.info("No time-based equity curve data available.")

# ===== STRATEGY RULES =====
st.markdown("---")
st.subheader("📖 Asian Hours Strategy Summary")

st.markdown("""
| Element | Rule |
|---------|------|
| **Session** | Enter only 00:00–11:00 UTC (Asia hours) |
| **Volatility Filter** | ATR-20 > median ATR-20 |
| **Mean-Reversion Long** | Price < lower Bollinger band AND RSI-14 < 30 |
| **Mean-Reversion Short** | Price > upper Bollinger band AND RSI-14 > 70 |
| **Breakout Long** | Price > 3-hour high AND RSI-14 > 60 |
| **Breakout Short** | Price < 3-hour low AND RSI-14 < 40 |
| **Stop-Loss** | 0.50% from entry |
| **Profit-Take** | Entry ± 3.0 × ATR-20 |
| **Exit** | First of stop-loss / profit-take / US session open (15:00–20:00 UTC) |
""")

# Footer
st.markdown("---")
st.caption(f"BTC Trading Strategy Dashboard | Data fetched from GitHub at {load_time}")
