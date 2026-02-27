import imgui
import numpy as np
import pandas as pd
from pathlib import Path


class StatsPanel:
    def __init__(self, sim_manager):
        self.sim_manager = sim_manager
        self.stats_data = []
        self.sort_column = 0  # 0=agent, 1=final_value, 2=volatility, 3=max_dd, 4=sharpe
        self.sort_ascending = True
        self.has_data = False
        self.csv_path = Path("logs/PortfolioHistory.csv")
        self._prev_running = False

    def clear(self):
        """Clear stats data."""
        self.stats_data = []
        self.has_data = False

    def _calculate_metrics(self, portfolio_series):
        """Calculate performance metrics for each agent."""
        results = []
        for agent_id, V_t in portfolio_series.items():
            if len(V_t) < 2:
                continue
            
            # Per-period returns
            r_t = np.diff(V_t) / V_t[:-1]
            
            # Filter out invalid returns
            r_t = r_t[np.isfinite(r_t)]
            if len(r_t) == 0:
                continue

            # Final total return
            final_portfolio_value = V_t[-1]
            
            # Volatility
            vol = np.std(r_t, ddof=1) if len(r_t) > 1 else 0.0
            
            # Max drawdown
            running_peak = np.maximum.accumulate(V_t)
            drawdowns = (V_t - running_peak) / running_peak
            max_dd = np.min(drawdowns)
            
            # Sharpe (assuming rf=0)
            sharpe = np.mean(r_t) / np.std(r_t) if np.std(r_t) > 0 else 0.0

            results.append({
                "agent": agent_id,
                "final_value": final_portfolio_value,
                "volatility": vol,
                "max_dd": max_dd,
                "sharpe": sharpe,
            })
        
        return results

    def _load_and_calculate(self):
        """Load portfolio history and calculate metrics."""
        if not self.csv_path.exists():
            print(f"Portfolio history file not found: {self.csv_path}")
            return

        try:
            df = pd.read_csv(self.csv_path)
            portfolio_series = {
                col: df[col].values 
                for col in df.columns 
                if col.lower() != "time" and col.lower() != "setup_agent"
            }
            self.stats_data = self._calculate_metrics(portfolio_series)
            self.has_data = True
            self._sort_data()
            print(f"Loaded stats for {len(self.stats_data)} agents")
        except Exception as e:
            print(f"Error loading portfolio history: {e}")

    def _sort_data(self):
        """Sort stats data by current column."""
        if not self.stats_data:
            return
        
        key_map = ["agent", "final_value", "volatility", "max_dd", "sharpe"]
        key = key_map[self.sort_column]
        self.stats_data.sort(key=lambda x: x[key], reverse=not self.sort_ascending)

    def render(self):
        imgui.set_next_window_position(320, 730, imgui.ONCE)
        imgui.set_next_window_size(1280, 330, imgui.ONCE)

        if imgui.begin("Performance Statistics"):
            # Check if simulation just stopped
            is_running = self.sim_manager.is_running()
            if self._prev_running and not is_running:
                # Simulation just finished
                self._load_and_calculate()
            self._prev_running = is_running

            if not self.has_data:
                imgui.text("Run a simulation to see performance statistics.")
            else:
                # Table header
                flags = (
                    imgui.TABLE_BORDERS
                    | imgui.TABLE_ROW_BACKGROUND
                    | imgui.TABLE_SIZING_FIXED_FIT
                )
                
                if imgui.begin_table("stats_table", 5, flags):
                    # Setup columns
                    imgui.table_setup_column("Agent", imgui.TABLE_COLUMN_WIDTH_FIXED, 200)
                    imgui.table_setup_column("Final Value", imgui.TABLE_COLUMN_WIDTH_FIXED, 150)
                    imgui.table_setup_column("Volatility", imgui.TABLE_COLUMN_WIDTH_FIXED, 150)
                    imgui.table_setup_column("Max Drawdown", imgui.TABLE_COLUMN_WIDTH_FIXED, 150)
                    imgui.table_setup_column("Sharpe", imgui.TABLE_COLUMN_WIDTH_FIXED, 150)

                    # Header row with clickable sorting
                    imgui.table_next_row(imgui.TABLE_ROW_HEADERS)
                    headers = ["Agent", "Final Value", "Volatility", "Max Drawdown", "Sharpe"]
                    for col_idx, header in enumerate(headers):
                        imgui.table_set_column_index(col_idx)
                        # Add sort indicator
                        if self.sort_column == col_idx:
                            indicator = " ▼" if not self.sort_ascending else " ▲"
                        else:
                            indicator = ""
                        if imgui.selectable(f"{header}{indicator}##header{col_idx}", False)[0]:
                            if self.sort_column == col_idx:
                                self.sort_ascending = not self.sort_ascending
                            else:
                                self.sort_column = col_idx
                                self.sort_ascending = True
                            self._sort_data()

                    # Data rows
                    for row in self.stats_data:
                        imgui.table_next_row()
                        
                        imgui.table_set_column_index(0)
                        imgui.text(row["agent"])
                        
                        imgui.table_set_column_index(1)
                        imgui.text(f"{row['final_value']:.2f}")
                        
                        imgui.table_set_column_index(2)
                        imgui.text(f"{row['volatility']:.4f}")
                        
                        imgui.table_set_column_index(3)
                        imgui.text(f"{row['max_dd']:.2%}")
                        
                        imgui.table_set_column_index(4)
                        imgui.text(f"{row['sharpe']:.4f}")

                    imgui.end_table()

            imgui.end()
