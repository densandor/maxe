import argparse
import numpy as np
import matplotlib.pyplot as plt

from ohlc import generateCandles


def autocorrelation(logReturns, lags=[1, 10, 30, 60, 120, 300, 600, 900]):
    mean = np.mean(logReturns)
    centeredLogReturns = logReturns - mean

    variance = np.sum(centeredLogReturns ** 2)

    results = np.zeros(len(lags) + 1)
    results[0] = 1.0
    for i, lag in enumerate(lags):
        gamma_k = np.sum(centeredLogReturns[:-lag] * centeredLogReturns[lag:])
        results[i+1] = gamma_k / variance
    return results


def heavyTails(logReturns):
    mean = np.mean(logReturns)
    standardDeviation = np.std(logReturns, ddof=0)
    z = (logReturns - mean) / standardDeviation
    fourthMoment = np.mean(z ** 4)
    excessKurtosis = fourthMoment - 3.0
    return excessKurtosis


def plotReturnsWithNormal(logReturns, bins=20, title="Log returns vs normal"):
    logReturns = np.asarray(logReturns)
    mean = np.mean(logReturns)
    standardDeviation = np.std(logReturns, ddof=0)

    plt.figure(figsize=(8, 5))

    plt.hist(
        logReturns,
        bins=bins,
        density=True,
        alpha=0.5,
        color="red",
        label="Empirical returns",
        histtype="step"
    )

    x = np.linspace(logReturns.min(), logReturns.max(), 500)
    norm_pdf = (1.0 / (np.sqrt(2 * np.pi) * standardDeviation)) * np.exp(-0.5 * ((x - mean) / standardDeviation) ** 2)
    plt.plot(x, norm_pdf, "b-", linewidth=2)

    plt.xlabel("Log return")
    plt.ylabel("Density")
    plt.title(title)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.yscale("log")
    plt.show()


def autocorrelationVolatility(logReturns, max_lags=30, measure='absolute'):
    # Step 1: Create volatility measure
    if measure == 'absolute':
        volatility = np.abs(logReturns)
    else:  # squared
        volatility = logReturns ** 2
    
    n = len(volatility)
    mean = np.mean(volatility)
    centeredVolatility = volatility - mean
    
    # Step 2: Calculate lag-0 autocovariance
    gamma_0 = np.sum(centeredVolatiliity ** 2) / n
    
    # Step 3: Calculate ACF at each lag
    acf_vol = np.zeros(max_lags + 1)
    acf_vol[0] = 1.0
    
    for k in range(1, max_lags + 1):
        gamma_k = np.sum(centeredVolatiliity[:-k] * centeredVolatiliity[k:]) / n
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

    ohlc = generateCandles("logs/TradeLog.csv", timeframeSeconds=args.timeframe)

    closePrices = ohlc["close"].values

    logReturns = np.log(closePrices[1:] / closePrices[:-1])

    lagsToCalculate = [60, 300]
    autocorrelationResults = autocorrelation(logReturns, lags=lagsToCalculate)
    print("Autocorrelation Function (ACF) of Returns:")
    for i in range(len(lagsToCalculate)):
        print("Lag " + str(lagsToCalculate[i]) + ": " + str(autocorrelationResults[i + 1]))

    excessKurtosis = heavyTails(logReturns)
    print("\nExcess Kurtosis of Returns: " + str(excessKurtosis))

    plotReturnsWithNormal(logReturns)
