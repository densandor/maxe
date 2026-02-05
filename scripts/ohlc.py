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