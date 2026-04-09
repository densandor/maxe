import argparse
import pandas as pd
import matplotlib.pyplot as plt

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser("mao")
    parser.add_argument("input", nargs="?", default="logs/MarketDataLog.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    
    plt.figure(figsize=(12, 6))
    plt.plot(df['time'], df['price'], label='Price', linewidth=1, color='blue', alpha=0.7)
    plt.plot(df['time'], df['fastEma'], label='Fast EMA', linewidth=1, color='red', alpha=0.7)
    plt.plot(df['time'], df['slowEma'], label='Slow EMA', linewidth=1, color='green', alpha=0.7)
    
    plt.xlabel('Simulation Steps')
    plt.ylabel('Asset Price')
    plt.title('Price and Moving Averages')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
