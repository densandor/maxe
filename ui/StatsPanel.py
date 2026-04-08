import imgui
import pandas as pd
from pathlib import Path

from scripts.performanceMetrics import agentPerformanceMetrics


class StatsPanel:
    def __init__(self, simManager):
        self.simManager = simManager
        self.statsData = []
        self.sortColumn = 0
        self.sortAscending = True
        self.hasData = False
        self.csvPath = Path("logs/PortfolioLog.csv")
        self._prevRunning = False

    def clear(self):
        self.statsData = []
        self.hasData = False

    def _loadAndCalculate(self):
        df = pd.read_csv(self.csvPath)
        portfolioSeries = {
            col: df[col].values 
            for col in df.columns 
            if col.lower() != "time" and col.lower() != "setup_agent"
        }
        resultsDF = agentPerformanceMetrics(portfolioSeries)
        self.statsData = []
        for _, row in resultsDF.iterrows():
            self.statsData.append({
                "agent": row["agent_name"],
                "final_value": row["final_portfolio_value"],
                "volatility": row["volatility"],
                "max_dd": row["max_drawdown"],
                "sharpe": row["sharpe_ratio"],
            })
        self.hasData = True
        self._sortData()
        print(f"Loaded stats for {len(self.statsData)} agents")

    def _sortData(self):      
        keyMap = ["agent", "final_value", "volatility", "max_dd", "sharpe"]
        key = keyMap[self.sortColumn]
        self.statsData.sort(key=lambda x: x[key], reverse=not self.sortAscending)

    def render(self):
        imgui.set_next_window_position(960, 720, imgui.ONCE)
        imgui.set_next_window_size(960, 360, imgui.ONCE)

        if imgui.begin("Performance Statistics"):
            # Check if simulation just stopped
            isRunning = self.simManager.is_running()
            if self._prevRunning and not isRunning:
                # Simulation just finished
                self._loadAndCalculate()
            self._prevRunning = isRunning

            if not self.hasData:
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
                    for colIdx, header in enumerate(headers):
                        imgui.table_set_column_index(colIdx)
                        # Add sort indicator
                        if self.sortColumn == colIdx:
                            indicator = " (Desc.)" if not self.sortAscending else " (Asc.)"
                        else:
                            indicator = ""
                        if imgui.selectable(f"{header}{indicator}##header{colIdx}", False)[0]:
                            if self.sortColumn == colIdx:
                                self.sortAscending = not self.sortAscending
                            else:
                                self.sortColumn = colIdx
                                self.sortAscending = True
                            self._sortData()

                    # Data rows
                    for row in self.statsData:
                        imgui.table_next_row()
                        
                        imgui.table_set_column_index(0)
                        imgui.text(row["agent"])
                        
                        imgui.table_set_column_index(1)
                        imgui.text(f"{row['final_value']:.2f}")
                        
                        imgui.table_set_column_index(2)
                        imgui.text(f"{row['volatility']:.4f}")
                        
                        imgui.table_set_column_index(3)
                        imgui.text(f"{row['max_dd']:.2f}")
                        
                        imgui.table_set_column_index(4)
                        imgui.text(f"{row['sharpe']:.4f}")

                    imgui.end_table()

            imgui.end()
