import argparse
import mplfinance as mpf
import pandas as pd

def generateCandles(csv, timeframeSeconds=60):
    df = pd.read_csv(csv)
    df.columns = ["id", "time", "price", "aggressing", "aggressingOwner", "direction", "resting", "restingOwner", "volume"]
    
    # Assume "time" column is in seconds
    df["dateTime"] = pd.to_datetime(df["time"], unit="s")
    
    # Create time buckets based on timeframe
    df["candleTime"] = df["dateTime"].dt.floor(str(timeframeSeconds) + "s")
    
    # Group by candle candle_time and calculate OHLC
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
    parser.add_argument("timeframe", nargs="?", default=60, type=int, help="The time (in seconds) that each candle should track.")
    args = parser.parse_args()

    df = generateCandles("logs/TradeLog.csv", timeframeSeconds=args.timeframe)
    df = df.set_index("time")
    #save = {"fname": str(args.timeframe) + "s_candles.png", "dpi":300, "bbox_inches": "tight"}
    mpf.plot(df, type="candle", style="default", title=str(args.timeframe) + "s Candles")
