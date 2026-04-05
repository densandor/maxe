import imgui
import numpy as np
import sys
from pathlib import Path
from OpenGL import GL as gl
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.pyplot as plt


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.candles import generateCandles
from scripts.stylisedFacts import (volatility, returnAutocorrelation, volatilityAutocorrelation, heavyTails, plotReturnsWithNormal)


class MarketAnalysisPanel:
    def __init__(self, simManager):
        self.simManager = simManager
        self.hasData = False
        self.tradeLogPath = Path("logs/TradeLog.csv")
        self._prevRunning = False
        self.useLogAxis = False
        self._histTextureId = None
        self._histTextureSize = (0, 0)
        
        # Metrics
        self.volatilityAbs = 0.0
        self.acfLags = [1, 6, 30, 90]
        self.retAcfValues = []
        self.volAcfValues = []
        self.excessKurtosis = 0.0
        
        # Chart data
        self.logReturns = None

        # Chart controls
        self.useLogAxis = False
        self.chartTextureId = None
        self.chartSize = (0, 0)
        self.chartNeedsRefresh = False

    def clear(self):
        self.hasData = False
        self.retAcfValues = []
        self.volAcfValues = []
        self.logReturns = None
        self.chartNeedsRefresh = False
        self._deleteChartTexture()

    def _deleteChartTexture(self):
        if self.chartTextureId is not None:
            gl.glDeleteTextures([self.chartTextureId])
            self.chartTextureId = None
            self.chartSize = (0, 0)

    def _refreshChartTexture(self):
        fig = plotReturnsWithNormal(
            self.logReturns,
            logScale=self.useLogAxis,
            show=False,
            title="Log Returns (Normal Distribution for Reference)",
        )
        fig.canvas.draw()

        rgba = np.asarray(fig.canvas.buffer_rgba(), dtype=np.uint8)
        h, w = rgba.shape[0], rgba.shape[1]

        self._deleteChartTexture()
        textureId = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, textureId)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, w, h, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, rgba)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        self.chartTextureId = textureId
        self.chartSize = (w, h)
        self.chartNeedsRefresh = False
        plt.close(fig)

    def _loadAndAnalyze(self):
        # Generate candles using shared function
        ohlc = generateCandles(str(self.tradeLogPath))
        
        # Calculate log returns
        closePrices = ohlc['close'].values
        self.logReturns = np.log(closePrices[1:] / closePrices[:-1])        
        
        # Calculate metrics using shared functions from stylisedFacts
        volAbs = volatility(self.logReturns)
        self.volatilityAbs = np.mean(volAbs)
        
        acfResults = returnAutocorrelation(self.logReturns, lags=self.acfLags)
        self.retAcfValues = list(acfResults[1:])  # skip lag-0
        
        volAcfResults = volatilityAutocorrelation(self.logReturns, lags=self.acfLags)
        self.volAcfValues = list(volAcfResults[1:])  # skip lag-0
        
        self.excessKurtosis = heavyTails(self.logReturns)
        self.chartNeedsRefresh = True
        
        self.hasData = True
        print(f"Market analysis complete: {len(self.logReturns)} returns analyzed")

    def _drawMatplotlibChart(self):
        if self.chartTextureId is None:
            imgui.text("Chart will appear after analysis runs.")
            return

        availW = max(100.0, imgui.get_content_region_available_width() - 10.0)
        availH = max(100.0, imgui.get_window_height() - imgui.get_cursor_pos_y() - 12.0)
        texW, texH = self.chartSize
        if texW <= 0 or texH <= 0:
            return

        aspect = texH / texW
        drawW = availW
        drawH = drawW * aspect

        if drawH > availH:
            drawH = availH
            drawW = drawH / aspect

        imgui.image(self.chartTextureId, drawW, drawH)

    def render(self):
        imgui.set_next_window_position(0, 720, imgui.ALWAYS)
        imgui.set_next_window_size(960, 360, imgui.ALWAYS)

        if imgui.begin("Market Analysis"):
            # Check if simulation just stopped
            isRunning = self.simManager.is_running()
            if self._prevRunning and not isRunning:
                self._loadAndAnalyze()
            self._prevRunning = isRunning

            if not self.hasData:
                imgui.text("Run a simulation to see market stylised facts.")
            else:
                imgui.begin_child("##stats_col", width=310, height=0, border=True)
                imgui.text("Stylised Facts Summary")
                imgui.separator()

                imgui.text(f"Volatility (abs):  {self.volatilityAbs:.6f}")
                imgui.text(f"Excess Kurtosis:   {self.excessKurtosis:.4f}")

                imgui.separator()
                imgui.text("ACF of Returns:")
                for lag, acf in zip(self.acfLags, self.retAcfValues):
                    imgui.text(f"  Lag {lag:>3d}:  {acf:>8.6f}")
                imgui.separator()
                imgui.text("ACF of Volatility of Returns:")
                for lag, acf in zip(self.acfLags, self.volAcfValues):
                    imgui.text(f"  Lag {lag:>3d}:  {acf:>8.6f}")
                imgui.end_child()

                imgui.same_line()
                imgui.begin_child("##hist_col", width=0, height=0, border=True)
                checkboxWidth = imgui.calc_text_size("Log axis").x + imgui.get_frame_height() + 14

                childWidth = imgui.get_content_region_available_width()
                checkboxWidth = imgui.calc_text_size("Log axis").x + imgui.get_frame_height() + imgui.get_style().item_inner_spacing.x

                imgui.text("Return Distribution")
                imgui.same_line()
                imgui.set_cursor_pos_x(max(0.0, childWidth - checkboxWidth - imgui.get_style().window_padding.x))
                changedLog, self.useLogAxis = imgui.checkbox("Log axis", self.useLogAxis)
                imgui.separator()

                # Refresh matplotlib texture when controls change
                if changedLog:
                    self.chartNeedsRefresh = True

                if self.chartNeedsRefresh:
                    self._refreshChartTexture()

                self._drawMatplotlibChart()
                imgui.end_child()

            imgui.end()
