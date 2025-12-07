import argparse
import mplfinance as mpf
from ohlc import generate_candles

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser("chart")
    parser.add_argument("timeframe", nargs="?", default=10, type=int, help="The time (in seconds) that each candle should track.")
    args = parser.parse_args()

    df = generate_candles("logs/TradeLog.csv", timeframe_seconds=args.timeframe) # returns DataFrame indexed by datetime with columns Open,High,Low,Close,Volume
    df = df.set_index("time")

    mpf.plot(df, type="candle", volume=True, style="charles", title=str(args.timeframe) + "s Candles")