import argparse
import mplfinance as mpf
from ohlc import generateCandles

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser("chart")
    parser.add_argument("timeframe", nargs="?", default=60, type=int, help="The time (in seconds) that each candle should track.")
    args = parser.parse_args()

    df = generateCandles("logs/TradeLog.csv", timeframeSeconds=args.timeframe) # returns DataFrame indexed by datetime with columns Open,High,Low,Close,Volume
    df = df.set_index("time")
    save = {"fname": str(args.timeframe) + "s_candles.png", "dpi":300, "bbox_inches": "tight"}
    mpf.plot(df, type="candle", style="default", title=str(args.timeframe) + "s Candles")
