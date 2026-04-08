import numpy as np
import pandas as pd
import argparse


def agentPerformanceMetrics(portfolioSeries):
    results = []
    for agentName, portfolio in portfolioSeries.items():

        portfolio = np.asarray(portfolio, dtype=float)

        # Per-period returns (for calculating other metrics)
        returns = np.diff(portfolio)

        # Final total return
        finalPortfolioValue = portfolio[-1]
                
        # Volatility
        volatility = np.std(returns, ddof=1)
        
        # Max drawdown
        runningPeak = np.maximum.accumulate(portfolio)
        drawdowns = runningPeak - portfolio
        maxDrawdown = np.max(drawdowns)
        
        # Sharpe (assuming rf=0)
        sharpe = np.mean(returns) / np.std(returns)

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
    parser.add_argument("input", nargs="?", default="logs/PortfolioLog.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    portfolio_series = {col: df[col].values for col in df.columns if col.lower() != "time" and col.lower() != "setup_agent"}
    results = agentPerformanceMetrics(portfolio_series)
    print("\nSummary of Performance Metrics:")
    print(results)
