import argparse
import numpy as np
import matplotlib.pyplot as plt
from scripts.candles import generateCandles


# Volatility of the returns (estimated as the absolute value)
def volatility(logReturns):
    return np.abs(logReturns)

# Autocorrelation of returns (short-term memory)
def returnAutocorrelation(logReturns, lags=[1, 10, 30, 90]):
    mean = np.mean(logReturns)
    centeredLogReturns = logReturns - mean

    variance = np.sum(centeredLogReturns ** 2)

    results = np.zeros(len(lags) + 1)
    results[0] = 1.0
    for i, lag in enumerate(lags):
        results[i+1] = np.sum(centeredLogReturns[:-lag] * centeredLogReturns[lag:]) / variance
    return results

# Autocorrelation of the volatility of the returns (volatility clustering)
def volatilityAutocorrelation(logReturns, lags=[1, 10, 30, 90]):
    vol = volatility(logReturns)
    
    n = len(vol)
    mean = np.mean(vol)
    centeredVolatility = vol - mean
    
    # Calculate lag-0 autocovariance
    lag0 = np.sum(centeredVolatility ** 2) / n
    
    # Calculate ACF at each lag
    results = np.zeros(len(lags) + 1)
    results[0] = 1.0
    
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

def plotReturnsWithNormal(logReturns, bins=50, title="Log Returns (Normal Distribution for Reference)", logScale=True, show=True, returnFigure=False):
    logReturns = np.asarray(logReturns)
    mean = np.mean(logReturns)
    standardDeviation = np.std(logReturns)

    fig = plt.figure(figsize=(8, 5))

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
    if show:
        plt.show()
    if returnFigure:
        return fig
    if not show:
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("chart")
    parser.add_argument("timeframe", nargs="?", default=60, type=int, help="The time (in seconds) that each candle should track.")
    args = parser.parse_args()

    ohlc = generateCandles("logs/TradeLog.csv", timeframeSeconds=args.timeframe)
    closePrices = ohlc["close"].values
    logReturns = np.log(closePrices[1:] / closePrices[:-1])

    vol = volatility(logReturns)
    print("Mean Volatility of Returns: " + str(np.mean(vol)))

    lagsToCalculate = [1, 10, 30, 90]

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
