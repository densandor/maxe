from pathlib import Path
import mplfinance as mpf
import pandas as pd
from ohlc import generate_candles

if __name__ == "__main__":
    
    df = generate_candles("logs/TradeLog.csv", timeframe_seconds=10) # returns DataFrame indexed by datetime with columns Open,High,Low,Close,Volume
    df = df.set_index("time")

    mpf.plot(df, type="candle", volume=True, style="charles", title="10s Candles")