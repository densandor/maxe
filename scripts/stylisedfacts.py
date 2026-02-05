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
    
    if standardDeviation == 0:
        return np.nan

    z = (logReturns - mean) / standardDeviation
    fourthMoment = np.mean(z ** 4)
    excessKurtosis = fourthMoment - 3.0
    return excessKurtosis


def plotReturnsWithNormal(logReturns, bins=25, title="Log returns vs normal"):
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