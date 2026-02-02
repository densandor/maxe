import argparse
import numpy as np
import matplotlib.pyplot as plt
from ohlc import generate_candles


def calculate_acf_returns(log_returns, max_lags=20):
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


def calculate_acf_volatility(log_returns, max_lags=30, measure='absolute'):
    # Step 1: Create volatility measure
    if measure == 'absolute':
        vol = np.abs(log_returns)
    else:  # squared
        vol = log_returns ** 2
    
    n = len(vol)
    mu_vol = np.mean(vol)
    centered_vol = vol - mu_vol
    
    # Step 2: Calculate lag-0 autocovariance
    gamma_0 = np.sum(centered_vol ** 2) / n
    
    # Step 3: Calculate ACF at each lag
    acf_vol = np.zeros(max_lags + 1)
    acf_vol[0] = 1.0
    
    for k in range(1, max_lags + 1):
        gamma_k = np.sum(centered_vol[:-k] * centered_vol[k:]) / n
        acf_vol[k] = gamma_k / gamma_0
    
    # Step 4: Estimate decay exponent (optional)
    # Fit log(ACF) = -β*log(lag) using lags where ACF > threshold
    lags_for_fit = np.arange(2, min(15, max_lags))
    acf_for_fit = acf_vol[lags_for_fit]
    
    decay_exp = np.nan
    if np.sum(acf_for_fit > 0.01) > 3:
        valid_mask = acf_for_fit > 0.01
        lags_valid = lags_for_fit[valid_mask]
        acf_valid = acf_for_fit[valid_mask]
        
        # Linear regression on log-log scale
        log_lags = np.log(lags_valid)
        log_acf = np.log(acf_valid)
        
        # Slope = -β (note the minus sign)
        n_pts = len(log_lags)
        numerator = n_pts * np.sum(log_lags * log_acf) - np.sum(log_lags) * np.sum(log_acf)
        denominator = n_pts * np.sum(log_lags**2) - np.sum(log_lags)**2
        slope = numerator / denominator
        decay_exp = -slope
    
    return acf_vol, decay_exp


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
    max_lags = 200
    acf_values = calculate_acf_returns(log_returns, max_lags=max_lags)

    plt.plot([lag+1 for lag in range(max_lags+1)], acf_values)
    plt.xlabel("Lag")
    plt.ylabel("Autocorrelation")
    plt.legend()
    plt.show()

    acf_vol, decay_exp = calculate_acf_volatility(log_returns, max_lags=15, measure='absolute')
    print(f"Volatility Clustering (lag-1):  {acf_vol[1]}  [expect: 0.3-0.6]")