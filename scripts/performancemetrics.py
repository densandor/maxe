import numpy as np
import pandas as pd
import argparse

def agentPerformanceMetrics(portfolioSeries):
    results = []
    for agentName, portfolioValueSeries in portfolioSeries.items():
        # Per-period returns (for calculating other metrics)
        returnSeries = np.diff(portfolioValueSeries) / portfolioValueSeries[:-1]

        # Final total return
        finalPortfolioValue = portfolioValueSeries[-1]
                
        # Volatility
        volatility = np.std(returnSeries, ddof=1)
        
        # Max drawdown
        runningPeak = np.maximum.accumulate(portfolioValueSeries)
        drawdowns = (portfolioValueSeries - runningPeak) / runningPeak
        maxDrawdown = np.min(drawdowns)
        
        # Sharpe (assuming rf=0)
        sharpe = np.mean(returnSeries) / np.std(returnSeries)

        results.append({
            "agent_name": agentName,
            "final_portfolio_value": finalPortfolioValue,
            "volatility": volatility,
            "max_drawdown": maxDrawdown,
            "sharpe_ratio": sharpe,
        })
        
    return pd.DataFrame(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser("mao")
    parser.add_argument("input", nargs="?", default="logs/PortfolioHistory.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    portfolio_series = {col: df[col].values for col in df.columns if col.lower() != "time" and col.lower() != "setup_agent"}
    results = agentPerformanceMetrics(portfolio_series)
    print("\nSummary of Performance Metrics:")
    print(results)