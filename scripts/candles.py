import argparse
import mplfinance as mpf
import pandas as pd

def generateCandles(csv, timeframe=10):
    df = pd.read_csv(csv)
    df.columns = ["id", "time", "price", "aggressing", "aggressingOwner", "direction", "resting", "restingOwner", "volume"]

    # Group directly by simulation-step buckets (no datetime conversion).
    bucket = max(1, int(timeframe))
    df["candleTime"] = (df["time"] // bucket) * bucket

    # Group by candle bucket and calculate OHLC.
    candles = df.groupby("candleTime").agg(
        open=("price", "first"),
        high=("price", "max"),
        low=("price", "min"),
        close=("price", "last"),
        volume=("price", "count")
    ).reset_index()
    
    candles.rename(columns={"candleTime": "time"}, inplace=True)
    
    return candles

if __name__ == "__main__":
    parser = argparse.ArgumentParser("chart")
    parser.add_argument("timeframe", nargs="?", default=10, type=int, help="The number of time steps that each candle should track.")
    args = parser.parse_args()

    df = generateCandles("logs/TradeLog.csv", timeframe=args.timeframe)
    df = df.set_index("time")
    #save = {"fname": str(args.timeframe) + "s_candles.png", "dpi":300, "bbox_inches": "tight"}
    mpf.plot(df, type="candle", style="default", title=str(args.timeframe) + "s Candles")
