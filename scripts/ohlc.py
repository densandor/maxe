import pandas as pd

def generate_candles(csv_file, timeframe_seconds=60):
    
    df = pd.read_csv(csv_file)
    
    df.columns = ["id", "time", "price", "aggressing", "aggressingOwner", "direction", "resting", "restingOwner", "volume"]
    
    # Assume "time" is in milliseconds
    df["datetime"] = pd.to_datetime(df["time"], unit="ms")
    
    # Create time buckets based on timeframe
    df["candle_time"] = df["datetime"].dt.floor(f"{timeframe_seconds}s")
    
    # Group by candle candle_time and calculate OHLC
    candles = df.groupby("candle_time").agg(
        open=("price", "first"),
        high=("price", "max"),
        low=("price", "min"),
        close=("price", "last"),
        volume=("price", "count")
    ).reset_index()
    
    candles.rename(columns={"candle_time": "time"}, inplace=True)
    
    return candles