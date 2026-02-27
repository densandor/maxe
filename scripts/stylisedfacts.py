import argparse
import numpy as np
import matplotlib.pyplot as plt
from scripts.candles import generateCandles

# Volatility of the mid-price
def volatility(logReturns, measure="absolute"):
    if measure == "absolute":
        return np.abs(logReturns)
    elif measure == "squared":
        return logReturns ** 2
    else:
        raise ValueError("Invalid measure. Use 'absolute' or 'squared'.")

# Autocorrelation of returns (short-term memory)
def returnAutocorrelation(logReturns, lags=[1, 10, 30, 60, 120, 300, 600, 900]):
    mean = np.mean(logReturns)
    centeredLogReturns = logReturns - mean

    variance = np.sum(centeredLogReturns ** 2)

    results = np.zeros(len(lags) + 1)
    results[0] = 1.0
    for i, lag in enumerate(lags):
        results[i+1] = np.sum(centeredLogReturns[:-lag] * centeredLogReturns[lag:]) / variance
    return results

# Autocorrelation of the volatility of the mid-price (volatility clustering)
def volatilityAutocorrelation(logReturns, lags=[1, 10, 30, 60, 120, 300, 600, 900], measure="absolute"):
    volatility = volatility(logReturns, measure=measure)
    
    n = len(volatility)
    mean = np.mean(volatility)
    centeredVolatility = volatility - mean
    
    # Calculate lag-0 autocovariance
    gamma_0 = np.sum(centeredVolatility ** 2) / n
    
    # Calculate ACF at each lag
    results = np.zeros(len(lags) + 1)
    results[0] = 1.0
    
    for i, lag in enumerate(lags):
        gamma_k = np.sum(centeredVolatility[:-lag] * centeredVolatility[lag:]) / n
        results[i+1] = gamma_k / gamma_0
    
    return results

# Excess kurtosis of returns (heavy tails)
def heavyTails(logReturns):
    mean = np.mean(logReturns)
    standardDeviation = np.std(logReturns)
    z = (logReturns - mean) / standardDeviation
    fourthMoment = np.mean(z ** 4)
    excessKurtosis = fourthMoment - 3.0
    return excessKurtosis

def plotReturnsWithNormal(logReturns, bins=20, title="Log Returns (Normal Distribution for Reference)", logScale=True):
    logReturns = np.asarray(logReturns)
    mean = np.mean(logReturns)
    standardDeviation = np.std(logReturns)

    plt.figure(figsize=(8, 5))

    plt.hist(logReturns, bins=bins, density=True, alpha=0.5, color="red", label="Empirical returns", histtype="step")

    x = np.linspace(logReturns.min(), logReturns.max(), 500)
    normalPDF = (1.0 / (np.sqrt(2 * np.pi) * standardDeviation)) * np.exp(-0.5 * ((x - mean) / standardDeviation) ** 2)
    plt.plot(x, normalPDF, "b-", linewidth=2)

    plt.xlabel("Log Return")
    plt.ylabel("Density")
    plt.title(title)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    if logScale:
        plt.yscale("log")
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("chart")
    parser.add_argument("timeframe", nargs="?", default=60, type=int, help="The time (in seconds) that each candle should track.")
    args = parser.parse_args()

    ohlc = generateCandles("logs/TradeLog.csv", timeframeSeconds=args.timeframe)
    closePrices = ohlc["close"].values
    logReturns = np.log(closePrices[1:] / closePrices[:-1])

    volatility = volatility(logReturns)
    print("Mean Volatility of Returns: " + str(volatility))

    lagsToCalculate = [60, 300]

    returnACF = returnAutocorrelation(logReturns, lags=lagsToCalculate)
    print("Autocorrelation Function (ACF) of Returns:")
    for i in range(len(lagsToCalculate)):
        print("Lag " + str(lagsToCalculate[i]) + ": " + str(returnACF[i + 1]))

    volatilityACF = volatilityAutocorrelation(logReturns, lags=lagsToCalculate)
    print("\nAutocorrelation Function (ACF) of Volatility:")
    for i in range(len(lagsToCalculate)):
        print("Lag " + str(lagsToCalculate[i]) + ": " + str(volatilityACF[i + 1]))

    excessKurtosis = heavyTails(logReturns)
    print("\nExcess Kurtosis of Returns: " + str(excessKurtosis))

    plotReturnsWithNormal(logReturns)
