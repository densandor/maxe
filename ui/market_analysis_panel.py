import imgui
import numpy as np
import sys
from pathlib import Path
from OpenGL import GL as gl
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.pyplot as plt


# Add project root to path for script imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.candles import generateCandles
from scripts.stylisedFacts import (
    volatility,
    returnAutocorrelation,
    volatilityAutocorrelation,
    heavyTails,
    plotReturnsWithNormal,
)


class MarketAnalysisPanel:
    def __init__(self, sim_manager):
        self.sim_manager = sim_manager
        self.has_data = False
        self.trade_log_path = Path("logs/TradeLog.csv")
        self._prev_running = False
        self.use_log_axis = False
        self._hist_texture_id = None
        self._hist_texture_size = (0, 0)
        
        # Metrics
        self.volatility_abs = 0.0
        self.acf_lags = [1, 6, 30, 90]
        self.ret_acf_values = []
        self.vol_acf_values = []
        self.excess_kurtosis = 0.0
        self.log_returns = None

    def clear(self):
        """Clear analysis data."""
        self.has_data = False
        self.ret_acf_values = []
        self.vol_acf_values = []
        self.log_returns = None
        self._delete_hist_texture()

    def _delete_hist_texture(self):
        if self._hist_texture_id is not None:
            gl.glDeleteTextures(int(self._hist_texture_id))
            self._hist_texture_id = None
            self._hist_texture_size = (0, 0)

    def _update_hist_texture(self, log_returns):
        fig = plotReturnsWithNormal(
            log_returns,
            logScale=self.use_log_axis,
            show=False,
            returnFigure=True,
        )

        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        width, height = canvas.get_width_height()
        rgba = np.asarray(canvas.buffer_rgba(), dtype=np.uint8)

        self._delete_hist_texture()

        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, rgba)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        self._hist_texture_id = texture_id
        self._hist_texture_size = (width, height)
        plt.close(fig)

    def _load_and_analyze(self):
        # Generate candles using shared function
        ohlc = generateCandles(str(self.trade_log_path))
        
        # Calculate log returns
        close_prices = ohlc['close'].values
        log_returns = np.log(close_prices[1:] / close_prices[:-1])
        
        # Filter out invalid returns
        log_returns = log_returns[np.isfinite(log_returns)]
        
        self.log_returns = log_returns
        
        # Calculate metrics using shared functions from stylisedFacts
        vol_abs = volatility(log_returns)
        self.volatility_abs = np.mean(vol_abs)
        
        acf_results = returnAutocorrelation(log_returns, lags=self.acf_lags)
        self.ret_acf_values = list(acf_results[1:])  # skip lag-0
        
        vol_acf_results = volatilityAutocorrelation(log_returns, lags=self.acf_lags)
        self.vol_acf_values = list(vol_acf_results[1:])  # skip lag-0
        
        self.excess_kurtosis = heavyTails(log_returns)
        self._update_hist_texture(log_returns)
        
        self.has_data = True
        print(f"Market analysis complete: {len(log_returns)} returns analyzed.")

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
                # ---------- LEFT COLUMN: stats ----------
                imgui.begin_child("##stats_col", width=310, height=0, border=True)
                imgui.text("Stylised Facts Summary")
                imgui.separator()

                imgui.text(f"Volatility (abs):  {self.volatility_abs:.6f}")
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

                # ---------- RIGHT COLUMN: histogram image ----------
                imgui.same_line()
                imgui.begin_child("##hist_col", width=0, height=0, border=True)
                header_start_x = imgui.get_cursor_pos_x()
                available_width = imgui.get_content_region_available().x
                checkbox_width = imgui.calc_text_size("Log axis").x + imgui.get_frame_height() + 14

                imgui.text("Return Distribution")
                imgui.same_line(0, 0)
                imgui.set_cursor_pos_x(max(header_start_x, header_start_x + available_width - checkbox_width))
                changed_log, self.use_log_axis = imgui.checkbox("Log axis", self.use_log_axis)
                imgui.separator()

                if changed_log and self.log_returns is not None:
                    self._update_hist_texture(self.log_returns)

                if self._hist_texture_id is None:
                    imgui.text("Histogram unavailable.")
                else:
                    avail = imgui.get_content_region_available()
                    tex_w, tex_h = self._hist_texture_size
                    scale = min(avail.x / max(tex_w, 1), avail.y / max(tex_h, 1))
                    scale = max(scale, 0.1)
                    draw_w = tex_w * scale
                    draw_h = tex_h * scale
                    imgui.image(self._hist_texture_id, draw_w, draw_h, (0, 0), (1, 1))

                imgui.end_child()

            imgui.end()
