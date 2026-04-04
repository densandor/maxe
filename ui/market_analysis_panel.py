import imgui
import numpy as np
import pandas as pd
import OpenGL.GL as gl
import matplotlib.pyplot as plt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.candles import generateCandles
from scripts.stylisedFacts import (volatility, returnAutocorrelation, volatilityAutocorrelation, heavyTails, plotReturnsWithNormal)


class MarketAnalysisPanel:
    def __init__(self, sim_manager):
        self.sim_manager = sim_manager
        self.has_data = False
        self.trade_log_path = Path("logs/TradeLog.csv")
        self._prev_running = False
        
        # Metrics
        self.volatility_abs = 0.0
        self.acf_lags = [1, 6, 30, 90]
        self.ret_acf_values = []
        self.vol_acf_values = []
        self.excess_kurtosis = 0.0
        
        # Chart data
        self.log_returns = None

        # Chart controls
        self.use_log_axis = False
        self.chart_texture_id = None
        self.chart_size = (0, 0)
        self.chart_needs_refresh = False

    def clear(self):
        """Clear analysis data."""
        self.has_data = False
        self.ret_acf_values = []
        self.vol_acf_values = []
        self.log_returns = None
        self.chart_needs_refresh = False
        self._delete_chart_texture()

    def _delete_chart_texture(self):
        if self.chart_texture_id is not None:
            gl.glDeleteTextures([self.chart_texture_id])
            self.chart_texture_id = None
            self.chart_size = (0, 0)

    def _refresh_chart_texture(self):
        """Render matplotlib chart and upload it to an OpenGL texture for ImGui."""

        fig = plotReturnsWithNormal(
            self.log_returns,
            logScale=self.use_log_axis,
            show=False,
            title="Log Returns (Normal Distribution for Reference)",
        )
        fig.canvas.draw()

        rgba = np.asarray(fig.canvas.buffer_rgba(), dtype=np.uint8)
        h, w = rgba.shape[0], rgba.shape[1]

        self._delete_chart_texture()
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, w, h, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, rgba)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        self.chart_texture_id = texture_id
        self.chart_size = (w, h)
        self.chart_needs_refresh = False
        plt.close(fig)

    def _load_and_analyze(self):
        """Load trade log and calculate stylised facts."""
        # Generate candles using shared function
        ohlc = generateCandles(str(self.trade_log_path))
        
        # Calculate log returns
        close_prices = ohlc['close'].values
        self.log_returns = np.log(close_prices[1:] / close_prices[:-1])        
        
        # Calculate metrics using shared functions from stylisedFacts
        vol_abs = volatility(self.log_returns)
        self.volatility_abs = np.mean(vol_abs)
        
        acf_results = returnAutocorrelation(self.log_returns, lags=self.acf_lags)
        self.ret_acf_values = list(acf_results[1:])  # skip lag-0
        
        vol_acf_results = volatilityAutocorrelation(self.log_returns, lags=self.acf_lags)
        self.vol_acf_values = list(vol_acf_results[1:])  # skip lag-0
        
        self.excess_kurtosis = heavyTails(self.log_returns)
        self.chart_needs_refresh = True
        
        self.has_data = True
        print(f"Market analysis complete: {len(self.log_returns)} returns analyzed")

    def _draw_matplotlib_chart(self):
        if self.chart_texture_id is None:
            imgui.text("Chart will appear after analysis runs.")
            return

        avail_w = max(100.0, imgui.get_content_region_available_width() - 10.0)
        avail_h = max(100.0, imgui.get_window_height() - imgui.get_cursor_pos_y() - 12.0)
        tex_w, tex_h = self.chart_size
        if tex_w <= 0 or tex_h <= 0:
            return

        aspect = tex_h / tex_w
        draw_w = avail_w
        draw_h = draw_w * aspect

        if draw_h > avail_h:
            draw_h = avail_h
            draw_w = draw_h / aspect

        imgui.image(self.chart_texture_id, draw_w, draw_h)

    def render(self):
        imgui.set_next_window_position(0, 720, imgui.ALWAYS)
        imgui.set_next_window_size(960, 360, imgui.ALWAYS)

        if imgui.begin("Market Analysis"):
            # Check if simulation just stopped
            is_running = self.sim_manager.is_running()
            if self._prev_running and not is_running:
                self._load_and_analyze()
            self._prev_running = is_running

            if not self.has_data:
                imgui.text("Run a simulation to see market stylised facts.")
            else:
                imgui.begin_child("##stats_col", width=310, height=0, border=True)
                imgui.text("Stylised Facts Summary")
                imgui.separator()

                imgui.text(f"Volatility (abs):  {self.volatility_abs:.6f}")
                imgui.text(f"Excess Kurtosis:   {self.excess_kurtosis:.4f}")

                imgui.separator()
                imgui.text("ACF of Returns:")
                for lag, acf in zip(self.acf_lags, self.ret_acf_values):
                    imgui.text(f"  Lag {lag:>3d}:  {acf:>8.6f}")
                imgui.separator()
                imgui.text("ACF of Volatility of Returns:")
                for lag, acf in zip(self.acf_lags, self.vol_acf_values):
                    imgui.text(f"  Lag {lag:>3d}:  {acf:>8.6f}")
                imgui.end_child()

                imgui.same_line()
                imgui.begin_child("##hist_col", width=0, height=0, border=True)

                child_width = imgui.get_content_region_available_width()
                checkbox_width = imgui.calc_text_size("Log axis").x + imgui.get_frame_height() + imgui.get_style().item_inner_spacing.x

                imgui.text("Return Distribution")
                imgui.same_line()
                imgui.set_cursor_pos_x(max(0.0, child_width - checkbox_width - imgui.get_style().window_padding.x))
                changed_log, self.use_log_axis = imgui.checkbox("Log axis", self.use_log_axis)
                imgui.separator()

                # Refresh matplotlib texture when controls change
                if changed_log:
                    self.chart_needs_refresh = True

                if self.chart_needs_refresh:
                    self._refresh_chart_texture()

                self._draw_matplotlib_chart()
                imgui.end_child()

            imgui.end()
