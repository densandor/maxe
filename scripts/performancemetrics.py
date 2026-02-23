import numpy as np
import pandas as pd
import argparse

def calculate_performance_metrics(portfolio_series):
    results = []
    for agent_id, V_t in portfolio_series.items():
        # Per-period returns (for calculating other metrics)
        r_t = np.diff(V_t) / V_t[:-1]

        # Final total return
        final_portfolio_value = V_t[-1]
                
        # Volatility
        vol = np.std(r_t, ddof=1)
        
        # Max drawdown
        running_peak = np.maximum.accumulate(V_t)
        drawdowns = (V_t - running_peak) / running_peak
        max_dd = np.min(drawdowns)
        
        # Sharpe (assuming rf=0)
        sharpe = np.mean(r_t) / np.std(r_t)

        results.append({
            "agent_id": agent_id,
            "final_portfolio_value": final_portfolio_value,
            "volatility": vol,
            "max_dd": max_dd,
            "sharpe": sharpe,
        })
        
        # Store results...
        print(f"Agent {agent_id}: Final Portfolio Value={final_portfolio_value:.2f}, Volatility={vol:.2%}, Max Drawdown={max_dd:.2%}, Sharpe={sharpe:.2f}")
    return pd.DataFrame(results)
if __name__ == "__main__":
    parser = argparse.ArgumentParser("mao")
    parser.add_argument("input", nargs="?", default="logs/PortfolioHistory.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    portfolio_series = {col: df[col].values for col in df.columns if col.lower() != "time" and col.lower() != "setup_agent"}
    results = calculate_performance_metrics(portfolio_series)
    print("\nSummary of Performance Metrics:")
    print(results)