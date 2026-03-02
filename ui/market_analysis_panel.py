import imgui
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add project root to path for script imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.candles import generateCandles
from scripts.stylisedFacts import (
    volatility,
    returnAutocorrelation,
    volatilityAutocorrelation,
    heavyTails
)


class MarketAnalysisPanel:
    def __init__(self, sim_manager):
        self.sim_manager = sim_manager
        self.has_data = False
        self.trade_log_path = Path("logs/TradeLog.csv")
        self._prev_running = False
        
        # Metrics
        self.volatility_abs = 0.0
        self.volatility_sq = 0.0
        self.acf_lags = [1, 10, 60, 300]
        self.ret_acf_values = []
        self.vol_acf_values = []
        self.excess_kurtosis = 0.0
        
        # Histogram data
        self.hist_bins = []
        self.hist_counts = []
        self.log_returns = None
        self.timeframe = 60  # seconds per candle

        # Histogram controls
        self.use_log_axis = False
        self.num_bins = 30

    def clear(self):
        """Clear analysis data."""
        self.has_data = False
        self.ret_acf_values = []
        self.vol_acf_values = []
        self.hist_bins = []
        self.hist_counts = []
        self.log_returns = None

    def _compute_histogram(self, log_returns, num_bins=30):
        """Compute histogram bins and counts."""
        counts, bin_edges = np.histogram(log_returns, bins=num_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Normalize to density
        bin_width = bin_edges[1] - bin_edges[0]
        density = counts / (len(log_returns) * bin_width)
        
        return bin_centers, density

    def _load_and_analyze(self):
        """Load trade log and calculate stylised facts."""
        if not self.trade_log_path.exists():
            print(f"Trade log not found: {self.trade_log_path}")
            return

        try:
            # Generate candles using shared function
            ohlc = generateCandles(str(self.trade_log_path), self.timeframe)
            if ohlc is None or len(ohlc) < 2:
                print("Insufficient candle data")
                return
            
            # Calculate log returns
            close_prices = ohlc['close'].values
            log_returns = np.log(close_prices[1:] / close_prices[:-1])
            
            # Filter out invalid returns
            log_returns = log_returns[np.isfinite(log_returns)]
            if len(log_returns) < 10:
                print("Insufficient valid returns")
                return
            
            self.log_returns = log_returns
            
            # Calculate metrics using shared functions from stylisedFacts
            vol_abs = volatility(log_returns, measure="absolute")
            vol_sq = volatility(log_returns, measure="squared")
            self.volatility_abs = np.mean(vol_abs)
            self.volatility_sq = np.mean(vol_sq)
            
            acf_results = returnAutocorrelation(log_returns, lags=self.acf_lags)
            self.ret_acf_values = list(acf_results[1:])  # skip lag-0
            
            vol_acf_results = volatilityAutocorrelation(log_returns, lags=self.acf_lags, measure="absolute")
            self.vol_acf_values = list(vol_acf_results[1:])  # skip lag-0
            
            self.excess_kurtosis = heavyTails(log_returns)
            
            # Compute histogram
            self.hist_bins, self.hist_counts = self._compute_histogram(log_returns, self.num_bins)
            
            self.has_data = True
            print(f"Market analysis complete: {len(log_returns)} returns analyzed")
            
        except Exception as e:
            print(f"Error in market analysis: {e}")
            import traceback
            traceback.print_exc()

    def _draw_histogram(self):
        """Draw histogram with normal overlay using imgui draw list."""
        if self.log_returns is None or len(self.hist_bins) == 0:
            return
        
        draw_list = imgui.get_window_draw_list()
        
        # Chart dimensions – sized to fit the right-hand child panel
        chart_w = 530
        chart_h = 220
        pad_left = 40
        pad_top = 5
        pad_bottom = 20
        
        origin = imgui.get_cursor_screen_position()
        ox, oy = origin.x + pad_left, origin.y + pad_top
        
        total_w = chart_w + pad_left + 10
        total_h = chart_h + pad_top + pad_bottom
        imgui.invisible_button("##histogram", total_w, total_h)
        
        # Background
        col_bg = imgui.get_color_u32_rgba(0.10, 0.10, 0.12, 1.0)
        col_hist = imgui.get_color_u32_rgba(0.85, 0.22, 0.20, 0.7)
        col_normal = imgui.get_color_u32_rgba(0.30, 0.60, 1.00, 1.0)
        col_label = imgui.get_color_u32_rgba(0.70, 0.70, 0.70, 1.0)
        
        draw_list.add_rect_filled(ox, oy, ox + chart_w, oy + chart_h, col_bg)
        
        # Scales
        x_min, x_max = self.hist_bins.min(), self.hist_bins.max()
        counts = self.hist_counts.copy()
        
        use_log = self.use_log_axis
        if use_log:
            counts = np.where(counts > 0, np.log10(counts), 0)
        
        y_max = counts.max() * 1.1
        
        if x_max == x_min or y_max == 0:
            return
        
        def x_of(val):
            return ox + ((val - x_min) / (x_max - x_min)) * chart_w
        
        def y_of(val):
            return oy + chart_h - (val / y_max) * chart_h
        
        # Draw histogram bars
        bar_width = chart_w / len(self.hist_bins)
        for i, (bin_center, count) in enumerate(zip(self.hist_bins, counts)):
            x = x_of(bin_center)
            y = y_of(count)
            draw_list.add_rect_filled(
                x - bar_width/2, y,
                x + bar_width/2, oy + chart_h,
                col_hist
            )
        
        # Draw normal distribution overlay
        mean = np.mean(self.log_returns)
        std = np.std(self.log_returns, ddof=0)
        
        x_range = np.linspace(x_min, x_max, 100)
        norm_pdf = (1.0 / (np.sqrt(2 * np.pi) * std)) * np.exp(-0.5 * ((x_range - mean) / std) ** 2)
        if use_log:
            norm_pdf = np.where(norm_pdf > 0, np.log10(norm_pdf), 0)
        
        for i in range(len(x_range) - 1):
            x1 = x_of(x_range[i])
            y1 = y_of(norm_pdf[i])
            x2 = x_of(x_range[i + 1])
            y2 = y_of(norm_pdf[i + 1])
            draw_list.add_line(x1, y1, x2, y2, col_normal, 2.0)
        
        # Axis labels
        draw_list.add_text(ox + chart_w/2 - 30, oy + chart_h + 2, col_label, "Log Returns")
        y_label = "log10(density)" if use_log else "Density"
        draw_list.add_text(ox - 35, oy + chart_h / 2 - 5, col_label, y_label)

    def render(self):
        imgui.set_next_window_position(0, 730, imgui.ONCE)
        imgui.set_next_window_size(960, 360, imgui.ONCE)

        if imgui.begin("Market Analysis"):
            # Check if simulation just stopped
            is_running = self.sim_manager.is_running()
            if self._prev_running and not is_running:
                self._load_and_analyze()
            self._prev_running = is_running

            if not self.has_data:
                imgui.text("Run a simulation to see market stylised facts.")
            else:
                # ---------- LEFT COLUMN: stats ----------
                imgui.begin_child("##stats_col", width=310, height=0, border=True)
                imgui.text("Stylised Facts Summary")
                imgui.separator()

                imgui.text(f"Volatility (abs):  {self.volatility_abs:.6f}")
                imgui.text(f"Volatility (sq):   {self.volatility_sq:.6f}")
                imgui.text(f"Excess Kurtosis:   {self.excess_kurtosis:.4f}")

                imgui.separator()
                imgui.text("Return ACF:")
                for lag, acf in zip(self.acf_lags, self.ret_acf_values):
                    imgui.text(f"  Lag {lag:>3d}:  {acf:>8.6f}")
                imgui.separator()
                imgui.text("Volatility ACF:")
                for lag, acf in zip(self.acf_lags, self.vol_acf_values):
                    imgui.text(f"  Lag {lag:>3d}:  {acf:>8.6f}")
                imgui.end_child()

                # ---------- RIGHT COLUMN: histogram ----------
                imgui.same_line()
                imgui.begin_child("##hist_col", width=0, height=0, border=True)

                imgui.text("Return Distribution")
                imgui.separator()

                # Controls row
                changed_log, self.use_log_axis = imgui.checkbox("Log axis", self.use_log_axis)
                imgui.same_line(spacing=20)
                imgui.push_item_width(100)
                changed_bins, self.num_bins = imgui.input_int("Bins", self.num_bins, step=5)
                imgui.pop_item_width()
                if self.num_bins < 5:
                    self.num_bins = 5
                if self.num_bins > 500:
                    self.num_bins = 500

                # Recompute histogram when controls change
                if changed_log or changed_bins:
                    self.hist_bins, self.hist_counts = self._compute_histogram(
                        self.log_returns, self.num_bins
                    )

                self._draw_histogram()
                imgui.end_child()

            imgui.end()
