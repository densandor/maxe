import argparse
import numpy as np
import matplotlib.pyplot as plt
from scripts.candles import generateCandles

# Volatiliity of returns (estimated as the absolute returns)
def volatility(logReturns):
    return np.abs(logReturns)

# Autocorrelation of returns (short-term memory)
def returnAutocorrelation(logReturns, lags=[1, 10, 30, 60, 120, 300, 600, 900]):
    mean = np.mean(logReturns)
    centeredLogReturns = logReturns - mean
    variance = np.sum(centeredLogReturns ** 2)

    results = np.zeros(len(lags) + 1)
    results[0] = 1.0

    for i, lag in enumerate(lags):
        if lag <= 0 or lag >= len(logReturns):
            print(f"Warning: Lag {lag} is out of bounds for the log returns data. Skipping this lag.")
            results[i + 1] = np.nan
            continue
        results[i+1] = np.sum(centeredLogReturns[:-lag] * centeredLogReturns[lag:]) / variance
    return results

# Autocorrelation of the volatility of returns (volatility clustering)
def volatilityAutocorrelation(logReturns, lags=[1, 10, 30, 60, 120, 300, 600, 900]):
    vol = volatility(logReturns)
    
    n = len(vol)
    results = np.zeros(len(lags) + 1)
    results[0] = 1.0

    mean = np.mean(vol)
    centeredVolatility = vol - mean
    
    # Calculate lag-0 autocovariance
    lag0 = np.sum(centeredVolatility ** 2) / n
    
    # Calculate ACF at each lag
    for i, lag in enumerate(lags):
        lagK = np.sum(centeredVolatility[:-lag] * centeredVolatility[lag:]) / n
        results[i+1] = lagK / lag0
    
    return results

# Excess kurtosis of returns (heavy tails)
def heavyTails(logReturns):
    mean = np.mean(logReturns)
    standardDeviation = np.std(logReturns)

    z = (logReturns - mean) / standardDeviation
    fourthMoment = np.mean(z ** 4)
    excessKurtosis = fourthMoment - 3.0
    return excessKurtosis

def plotReturnsWithNormal(logReturns, bins=30, title="Log Returns (Normal Distribution for Reference)", logScale=False, show=True):
    mean = np.mean(logReturns)
    standardDeviation = np.std(logReturns)

    fig = plt.figure(figsize=(8, 5))

    plt.hist(logReturns, bins=bins, density=True, alpha=0.5, color="red", label="Empirical returns", histtype="step")

    if standardDeviation > 0:
        x = np.linspace(mean - 4 * standardDeviation, mean + 4 * standardDeviation, 500)
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
    if show:
        plt.show()
    return fig


if __name__ == "__main__":
    parser = argparse.ArgumentParser("chart")
    parser.add_argument("timeframe", nargs="?", default=10, type=int, help="The time (in seconds) that each candle should track.")
    args = parser.parse_args()

    ohlc = generateCandles("logs/TradeLog.csv", timeframeSeconds=args.timeframe)
    closePrices = ohlc["close"].values
    logReturns = np.log(closePrices[1:] / closePrices[:-1])

    vol = volatility(logReturns)
    print("Mean Volatility of Returns: " + str(np.mean(vol)))

    lagsToCalculate = [1, 6, 30]

    returnACF = returnAutocorrelation(logReturns, lags=lagsToCalculate)
    print("Autocorrelation Function of Returns:")
    print("Lags " + str(lagsToCalculate) + ": " + str(returnACF))

    volatilityACF = volatilityAutocorrelation(logReturns, lags=lagsToCalculate)
    print("\nAutocorrelation Function of Volatility of Returns:")
    print("Lags " + str(lagsToCalculate) + ": " + str(volatilityACF))

    excessKurtosis = heavyTails(logReturns)
    print("\nExcess Kurtosis of Returns: " + str(excessKurtosis))

    plotReturnsWithNormal(logReturns, logScale=True)
