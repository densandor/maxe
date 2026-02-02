import argparse
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import acf

from ohlc import generate_candles

def calculate_acf_returns(log_returns, max_lags=20):
    """
    Calculate autocorrelation function of raw returns.
    
    Args:
        log_returns: numpy array of log returns
        max_lags: maximum lag to compute
    
    Returns:
        acf: array of autocorrelations at lags 0 to max_lags
    """
    n = len(log_returns)
    mu = np.mean(log_returns)
    centered = log_returns - mu
    
    # Lag-0 autocovariance (variance)
    gamma_0 = np.sum(centered ** 2) / n
    
    # Initialize ACF array
    acf = np.zeros(max_lags + 1)
    acf[0] = 1.0  # By definition
    
    # Calculate ACF for each lag
    for k in range(1, max_lags + 1):
        gamma_k = np.sum(centered[:-k] * centered[k:]) / n
        acf[k] = gamma_k / gamma_0
    
    return acf

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser("chart")
    parser.add_argument("timeframe", nargs="?", default=60, type=int, help="The time (in seconds) that each candle should track.")
    args = parser.parse_args()

    ohlc = generate_candles("logs/TradeLog.csv", timeframe_seconds=args.timeframe) # returns DataFrame indexed by datetime with columns Open,High,Low,Close,Volume
    # Load OHLC data
    close_prices = ohlc['close'].values

    # Calculate log returns (standard in finance)
    log_returns = np.log(close_prices[1:] / close_prices[:-1])

    print(f"Data ready: {len(log_returns)} returns from {len(close_prices)} prices")

    # Calculate ACF using custom function
    max_lags = 900
    acf_values = calculate_acf_returns(log_returns, max_lags=max_lags)
    print("Autocorrelation Function (ACF) of Returns:")
    for lag in range(len(acf_values)):
        print(f"Lag {lag}: {acf_values[lag]:.4f}")