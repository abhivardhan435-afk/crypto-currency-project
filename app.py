import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="Crypto Market Analysis", layout="wide")

# Title and Abstract
st.title("Cryptocurrency Market Analysis: Risk & Classification")
st.markdown("""
This dashboard implements the project logic: classifying coins by market cap and analyzing volatility/liquidity trends.
""")

# --- 1. Data Collection Module ---
@st.cache_data
def fetch_crypto_data():
    """
    Fetches market data from CoinGecko API.
    Falls back to synthetic data if API is rate limited.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 50,  # Analyze top 50 coins
        'page': 1,
        'sparkline': 'true',
        'price_change_percentage': '24h,7d'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Process API Data
        processed_data = []
        for coin in data:
            # Calculate a simple volatility metric (std dev of last 7 days prices if sparkline exists)
            prices = coin.get('sparkline_in_7d', {}).get('price', [])
            volatility = np.std(prices) / np.mean(prices) if prices else 0
            
            processed_data.append({
                'name': coin['name'],
                'symbol': coin['symbol'].upper(),
                'current_price': coin['current_price'],
                'market_cap': coin['market_cap'],
                'volume_24h': coin['total_volume'],
                'change_7d': coin['price_change_percentage_7d_in_currency'],
                'volatility': volatility, # Normalized volatility index
                'liquidity_ratio': coin['total_volume'] / coin['market_cap'] if coin['market_cap'] else 0
            })
            
        st.success("Successfully fetched live data from CoinGecko.")
        return pd.DataFrame(processed_data)

    except Exception as e:
        st.warning(f"API Error ({e}). Using Synthetic Data for Demonstration.")
        
        # Generate Realistic Synthetic Data
        np.random.seed(42)
        categories = ['Large-Cap', 'Mid-Cap', 'Small-Cap']
        
        data = []
        for i in range(50):
            # Simulate characteristic differences
            if i < 10: # Large Cap
                mcap = np.random.randint(10e9, 100e9)
                vol = np.random.uniform(0.01, 0.05)
                liq = np.random.uniform(0.05, 0.2)
            elif i < 30: # Mid Cap
                mcap = np.random.randint(1e9, 10e9)
                vol = np.random.uniform(0.05, 0.15)
                liq = np.random.uniform(0.02, 0.1)
            else: # Small Cap
                mcap = np.random.randint(10e6, 1e9)
                vol = np.random.uniform(0.15, 0.40)
                liq = np.random.uniform(0.001, 0.05)
                
            data.append({
                'name': f"Crypto-{i}",
                'symbol': f"C{i}",
                'current_price': np.random.uniform(1, 1000),
                'market_cap': mcap,
                'volume_24h': mcap * liq,
                'change_7d': np.random.uniform(-20, 20),
                'volatility': vol,
                'liquidity_ratio': liq
            })
            
        return pd.DataFrame(data)

# Load Data
df = fetch_crypto_data()

# --- 2. Classification Module ---
def classify_market_cap(mcap):
    if mcap >= 10e9: # > 10 Billion
        return 'Large-Cap'
    elif mcap >= 1e9: # 1 Billion to 10 Billion
        return 'Mid-Cap'
    else:
        return 'Small-Cap'

df['Category'] = df['market_cap'].apply(classify_market_cap)

# --- Navigation and Layout ---
tab1, tab2, tab3 = st.tabs(["Dashboard", "Market Data", "Risk Analysis"])

with tab1:
    st.subheader("Market Overview")
    col1, col2, col3 = st.columns(3)
    
    avg_vol_large = df[df['Category'] == 'Large-Cap']['volatility'].mean()
    avg_vol_small = df[df['Category'] == 'Small-Cap']['volatility'].mean()
    
    col1.metric("Large-Cap Volatility", f"{avg_vol_large:.2%}", "Stable", delta_color="normal")
    col2.metric("Small-Cap Volatility", f"{avg_vol_small:.2%}", "High Risk", delta_color="inverse")
    col3.metric("Total Market Cap", f"${df['market_cap'].sum()/1e9:.2f} B")

    st.subheader("Classification Distribution")
    
    fig = px.pie(df, names='Category', title='Market Cap Classification', 
                 color='Category', 
                 color_discrete_map={'Large-Cap':'royalblue', 'Mid-Cap':'cyan', 'Small-Cap':'lightcyan'})
    # Make chart immersive
    fig.update_layout(autosize=True, margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Classified Cryptocurrency Data")
    st.dataframe(df.style.format({
        'market_cap': '${:,.0f}', 
        'volume_24h': '${:,.0f}',
        'volatility': '{:.2%}'
    }))

with tab3:
    st.subheader("Advanced Risk Analytics")
    
    # Nested Tabs for Analysis as requested
    analysis_tab1, analysis_tab2 = st.tabs(["Volatility Graph", "Correlation Matrix"])
    
    with analysis_tab1:
        st.markdown("### Volatility vs. Liquidity Analysis")
        st.info("""
        **Statistical Analysis:**
        This scatter plot visualizes the relationship between **Liquidity Ratio** (Total Volume / Market Cap) and **Volatility**.
        
        *   **X-Axis (Liquidity):** Higher values indicate assets that are easier to buy/sell without impacting price. Large-cap coins typically sit further right.
        *   **Y-Axis (Volatility):** Higher values indicate unstable prices. Small-cap coins typically sit higher up.
        *   **Bubble Size:** Represents Market Capitalization.
        
        **Conclusion:** You should observe a general trend where larger bubbles (Large-Cap) are clustered towards the bottom-right (Stable & Liquid), while smaller bubbles (Small-Cap) are scattered towards the top-left (Volatile & Illiquid). This confirms the hypothesis that market cap is inversely correlated with risk.
        """)
        
        fig2 = px.scatter(df, x="liquidity_ratio", y="volatility", 
                          size="market_cap", color="Category", 
                          hover_name="name", log_x=True,
                          title="Risk Map: Volatility vs Liquidity",
                          labels={"liquidity_ratio": "Liquidity Ratio (Log Scale)", "volatility": "Volatility Index"},
                          color_discrete_map={'Large-Cap':'#00CC96', 'Mid-Cap':'#EF553B', 'Small-Cap':'#636EFA'})
        fig2.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=500)
        st.plotly_chart(fig2, use_container_width=True)
        
    with analysis_tab2:
        st.markdown("### Market Feature Correlation")
        st.info("""
        **Statistical Analysis:**
        The Heatmap below displays the Pearson correlation coefficient between key market metrics.
        
        *   **Close to 1 (Red/Hot):** Strong positive correlation. (e.g., Market Cap often correlates with Volume).
        *   **Close to -1 (Blue/Cold):** Strong negative correlation. (e.g., Volatility often negatively correlates with Market Cap).
        *   **Close to 0:** No linear relationship.
        
        **Conclusion:** A negative correlation between `market_cap` and `volatility` proves that as the size of the asset grows, its price stability generally improves. This is a key finding for building safer investment portfolios.
        """)
        
        corr = df[['market_cap', 'volatility', 'liquidity_ratio', 'change_7d']].corr()
        fig3 = px.imshow(corr, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r', 
                         title="Correlation Matrix of Market Features")
        fig3.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=500)
        st.plotly_chart(fig3, use_container_width=True)

# --- Outcomes Logic ---
st.sidebar.markdown("### Risk Detection Model")
risk_threshold = st.sidebar.slider("Volatility Risk Threshold", 0.0, 0.5, 0.1)
high_risk_coins = df[df['volatility'] > risk_threshold]
st.sidebar.warning(f"{len(high_risk_coins)} Coins identified as High Risk base on current threshold.")
if st.sidebar.checkbox("Show High Risk Assets"):
    st.sidebar.table(high_risk_coins[['symbol', 'Category', 'volatility']])
