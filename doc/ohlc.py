import pandas as pd
from datetime import datetime, timedelta

def generate_candles(csv_file, timeframe_seconds=60):
    
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
    # Assume first column is time (milliseconds), second is price
    # Adjust column names if different
    df.columns = ['time_ms', 'price']
    
    # Convert milliseconds to datetime
    df['time'] = pd.to_datetime(df['time_ms'], unit='ms')
    
    # Create time buckets based on timeframe
    df['candle_time'] = df['time'].dt.floor(f'{timeframe_seconds}S')
    
    # Group by candle time and calculate OHLC
    candles = df.groupby('candle_time').agg(
        open=('price', 'first'),
        high=('price', 'max'),
        low=('price', 'min'),
        close=('price', 'last'),
        volume=('price', 'count')
    ).reset_index()
    
    candles.rename(columns={'candle_time': 'time'}, inplace=True)
    
    return candles

if __name__ == "__main__":
    
    candles_10s = generate_candles('TradeLog.csv', timeframe_seconds=10)
    print(candles_10s.to_string(index=False))
    print(f"\nTotal candles: {len(candles_10s)}\n")
    
    # Export to CSV
    candles_10s.to_csv('candles_10s.csv', index=False)
    print("✓ Exported 10s candles to 'candles_10s.csv'")