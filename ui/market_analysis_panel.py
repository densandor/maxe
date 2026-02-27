import imgui
import numpy as np
import pandas as pd
from pathlib import Path


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
        self.acf_values = []
        self.excess_kurtosis = 0.0
        self.vol_decay_exp = 0.0
        
        # Histogram data
        self.hist_bins = []
        self.hist_counts = []
        self.log_returns = None
        self.timeframe = 60  # seconds per candle

    def clear(self):
        """Clear analysis data."""
        self.has_data = False
        self.acf_values = []
        self.hist_bins = []
        self.hist_counts = []
        self.log_returns = None

    def _generate_candles(self, trade_log_path, timeframe_seconds):
        """Generate OHLC candles from trade log."""
        df = pd.read_csv(trade_log_path)
        
        if 'time' not in df.columns or 'price' not in df.columns:
            print("Trade log missing 'time' or 'price' columns")
            return None
            
        df = df.sort_values('time')
        df['bucket'] = (df['time'] // timeframe_seconds) * timeframe_seconds
        
        ohlc = df.groupby('bucket').agg(
            open=('price', 'first'),
            high=('price', 'max'),
            low=('price', 'min'),
            close=('price', 'last')
        ).reset_index()
        
        return ohlc

    def _calculate_volatility(self, log_returns, measure='absolute'):
        """Calculate volatility of log returns."""
        if measure == 'absolute':
            return np.std(np.abs(log_returns), ddof=0)
        else:  # squared
            return np.std(log_returns ** 2, ddof=0)

    def _return_autocorrelation(self, log_returns, lags):
        """Calculate autocorrelation of returns at given lags."""
        mean = np.mean(log_returns)
        centered = log_returns - mean
        variance = np.sum(centered ** 2)
        
        results = []
        for lag in lags:
            if lag >= len(log_returns):
                results.append(0.0)
                continue
            gamma_k = np.sum(centered[:-lag] * centered[lag:])
            results.append(gamma_k / variance)
        return results

    def _excess_kurtosis(self, log_returns):
        """Calculate excess kurtosis (heavy tails)."""
        mean = np.mean(log_returns)
        std = np.std(log_returns, ddof=0)
        if std == 0:
            return 0.0
        z = (log_returns - mean) / std
        fourth_moment = np.mean(z ** 4)
        return fourth_moment - 3.0

    def _volatility_clustering(self, log_returns, max_lags=30, measure='absolute'):
        """Calculate volatility autocorrelation and decay exponent."""
        if measure == 'absolute':
            vol = np.abs(log_returns)
        else:
            vol = log_returns ** 2
        
        n = len(vol)
        mean = np.mean(vol)
        centered = vol - mean
        gamma_0 = np.sum(centered ** 2) / n
        
        acf_vol = np.zeros(max_lags + 1)
        acf_vol[0] = 1.0
        
        for k in range(1, max_lags + 1):
            gamma_k = np.sum(centered[:-k] * centered[k:]) / n
            acf_vol[k] = gamma_k / gamma_0
        
        # Estimate decay exponent
        lags_for_fit = np.arange(2, min(15, max_lags))
        acf_for_fit = acf_vol[lags_for_fit]
        
        decay_exp = 0.0
        if np.sum(acf_for_fit > 0.01) > 3:
            valid_mask = acf_for_fit > 0.01
            lags_valid = lags_for_fit[valid_mask]
            acf_valid = acf_for_fit[valid_mask]
            
            log_lags = np.log(lags_valid)
            log_acf = np.log(acf_valid)
            
            n_pts = len(log_lags)
            numerator = n_pts * np.sum(log_lags * log_acf) - np.sum(log_lags) * np.sum(log_acf)
            denominator = n_pts * np.sum(log_lags**2) - np.sum(log_lags)**2
            if denominator != 0:
                slope = numerator / denominator
                decay_exp = -slope
        
        return decay_exp

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
            # Generate candles
            ohlc = self._generate_candles(self.trade_log_path, self.timeframe)
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
            
            # Calculate metrics
            self.volatility_abs = self._calculate_volatility(log_returns, 'absolute')
            self.volatility_sq = self._calculate_volatility(log_returns, 'squared')
            self.acf_values = self._return_autocorrelation(log_returns, self.acf_lags)
            self.excess_kurtosis = self._excess_kurtosis(log_returns)
            self.vol_decay_exp = self._volatility_clustering(log_returns)
            
            # Compute histogram
            self.hist_bins, self.hist_counts = self._compute_histogram(log_returns)
            
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
        
        # Chart dimensions
        chart_w = 500
        chart_h = 250
        margin = 40
        
        origin = imgui.get_cursor_screen_position()
        ox, oy = origin.x, origin.y
        
        imgui.invisible_button("##histogram", chart_w + margin * 2, chart_h + margin)
        
        # Background
        col_bg = imgui.get_color_u32_rgba(0.10, 0.10, 0.12, 1.0)
        col_hist = imgui.get_color_u32_rgba(0.85, 0.22, 0.20, 0.7)
        col_normal = imgui.get_color_u32_rgba(0.30, 0.60, 1.00, 1.0)
        col_label = imgui.get_color_u32_rgba(0.70, 0.70, 0.70, 1.0)
        
        draw_list.add_rect_filled(ox, oy, ox + chart_w, oy + chart_h, col_bg)
        
        # Scales
        x_min, x_max = self.hist_bins.min(), self.hist_bins.max()
        y_max = self.hist_counts.max() * 1.1
        
        if x_max == x_min or y_max == 0:
            return
        
        def x_of(val):
            return ox + ((val - x_min) / (x_max - x_min)) * chart_w
        
        def y_of(val):
            return oy + chart_h - (val / y_max) * chart_h
        
        # Draw histogram bars
        bar_width = chart_w / len(self.hist_bins)
        for i, (bin_center, count) in enumerate(zip(self.hist_bins, self.hist_counts)):
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
        
        for i in range(len(x_range) - 1):
            x1 = x_of(x_range[i])
            y1 = y_of(norm_pdf[i])
            x2 = x_of(x_range[i + 1])
            y2 = y_of(norm_pdf[i + 1])
            draw_list.add_line(x1, y1, x2, y2, col_normal, 2.0)
        
        # Labels
        draw_list.add_text(ox + chart_w/2 - 50, oy + chart_h + 5, col_label, "Log Returns")
        draw_list.add_text(ox + 5, oy - 15, col_label, "Distribution")

    def render(self):
        imgui.set_next_window_position(0, 730, imgui.ONCE)
        imgui.set_next_window_size(320, 330, imgui.ONCE)

        if imgui.begin("Market Analysis"):
            # Check if simulation just stopped
            is_running = self.sim_manager.is_running()
            if self._prev_running and not is_running:
                self._load_and_analyze()
            self._prev_running = is_running

            if not self.has_data:
                imgui.text("Run a simulation to see")
                imgui.text("market stylised facts.")
            else:
                imgui.text("Stylised Facts Summary")
                imgui.separator()
                
                # Metrics table
                imgui.text(f"Volatility (abs):  {self.volatility_abs:.6f}")
                imgui.text(f"Volatility (sq):   {self.volatility_sq:.6f}")
                imgui.text(f"Excess Kurtosis:   {self.excess_kurtosis:.4f}")
                imgui.text(f"Vol. Decay Exp:    {self.vol_decay_exp:.4f}")
                
                imgui.separator()
                imgui.text("Return ACF:")
                for lag, acf in zip(self.acf_lags, self.acf_values):
                    imgui.text(f"  Lag {lag:>3d}:  {acf:>8.6f}")
                
                imgui.separator()
                imgui.text("Return Distribution:")
                self._draw_histogram()

            imgui.end()
