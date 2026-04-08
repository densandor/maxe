import imgui
import math


class Candle:
    def __init__(self, open_price, startTime):
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.startTime = startTime

    def update(self, price):
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price


class ChartPanel:
    def __init__(self, dataQueue):
        self.dataQueue = dataQueue
        self.ticks = [] # (time, price) ticks
        self.candles = [] # Aggregated Candle objects
        self.timeframe = 50 # Time steps per candle
        self.visibleCandles = 200 # Maximum number of candles shown at once
        self._dirty = False # Flag to re-aggregate
        self.chartModes = ["Candle", "Line"]
        self.chartModeIndex = 0 

    def clear(self):
        self.ticks.clear()
        self.candles.clear()
        self._dirty = False

    def _aggregateAll(self):
        self.candles.clear()
        if not self.ticks:
            return
        current = None
        for time, price in self.ticks:
            bucket = int(time // self.timeframe) * self.timeframe
            if current is None or current.startTime != bucket:
                if current is not None:
                    self.candles.append(current)
                current = Candle(price, bucket)
            else:
                current.update(price)
        if current is not None:
            self.candles.append(current)

    def _processTick(self, time, price):
        bucket = int(time // self.timeframe) * self.timeframe
        if not self.candles or self.candles[-1].startTime != bucket:
            self.candles.append(Candle(price, bucket))
        else:
            self.candles[-1].update(price)

    def render(self):
        imgui.set_next_window_position(320, 0, imgui.ALWAYS)
        imgui.set_next_window_size(1280, 720, imgui.ALWAYS)

        if imgui.begin("Price Chart"):
            while len(self.dataQueue) > 0:
                try:
                    time, price = self.dataQueue.popleft()
                    self.ticks.append((time, price))
                    if not self._dirty:
                        self._processTick(time, price)
                except IndexError:
                    break

            # Timeframe and chart mode
            imgui.push_item_width(120)
            changed, newTimeframe = imgui.input_int("Timeframe (simulation steps)", self.timeframe, 1, 50)
            imgui.pop_item_width()
            if changed:
                newTimeframe = max(1, newTimeframe)
                if newTimeframe != self.timeframe:
                    self.timeframe = newTimeframe
                    self._dirty = True

            imgui.same_line()
            imgui.push_item_width(90)
            _, self.chartModeIndex = imgui.combo("Chart Mode", self.chartModeIndex, self.chartModes)
            imgui.pop_item_width()

            if self._dirty:
                self._aggregateAll()
                self._dirty = False

            if self.candles:
                visible = self.candles[-self.visibleCandles:]
                if self.ticks:
                    currentStep = int(self.ticks[-1][0])
                else:
                    currentStep = 0
                info = f"Time Step: {currentStep:>8d}"
                marginRight = 77 
                rightEdge = imgui.get_window_width() - marginRight
                textWidth = imgui.calc_text_size(info).x
                imgui.same_line(rightEdge - textWidth)
                imgui.text(info)

            if self.candles:
                if self.chartModeIndex == 0:
                    self._drawCandles(visible)
                else:
                    self._drawLine(visible)
            else:
                imgui.text("Run a simulation to see the chart.")

            imgui.end()

    def _drawCandles(self, candles):
        drawList = imgui.get_window_draw_list()

        avail = imgui.get_content_region_available()
        chartWidth = avail.x - 70
        chartHeight = avail.y - 54

        origin = imgui.get_cursor_screen_position()
        originX, originY = origin.x, origin.y

        # Reserving the full area so imgui knows it is used
        imgui.invisible_button("##chart", avail.x, avail.y - 30)

        rawMin = min(c.low for c in candles)
        rawMax = max(c.high for c in candles)
        priceMin = math.floor(rawMin * 0.95 / 10) * 10
        priceMax = math.ceil(rawMax * 1.05 / 10) * 10
        priceRange = priceMax - priceMin if priceMax != priceMin else 1.0

        def y_of(price):
            return originY + chartHeight - ((price - priceMin) / priceRange) * chartHeight

        # Candles
        numCandles = len(candles)
        totalWidth = chartWidth / max(numCandles, 1)
        bodyWidth = max(totalWidth * 0.7, 2)
        gap = (totalWidth - bodyWidth) / 2

        # Colours (RGBA)
        colorBull = imgui.get_color_u32_rgba(0.15, 0.75, 0.35, 1.0)
        colorBear = imgui.get_color_u32_rgba(0.85, 0.22, 0.20, 1.0)
        colorLabel = imgui.get_color_u32_rgba(0.70, 0.70, 0.70, 1.0)
        colorBg = imgui.get_color_u32_rgba(0.10, 0.10, 0.12, 1.0)

        # Background
        drawList.add_rect_filled(originX, originY, originX + chartWidth, originY + chartHeight, colorBg)

        # Price labels
        priceStep = 5
        firstLevel = int(priceMin / priceStep) * priceStep
        if firstLevel < priceMin:
            firstLevel += priceStep
        level = firstLevel
        while level <= priceMax:
            labelY = y_of(level)
            drawList.add_text(originX + chartWidth + 6, labelY - 7, colorLabel, f"{level:.2f}")
            level += priceStep

        # Candles
        for i, candle in enumerate(candles):
            xLeft = originX + gap + i * totalWidth
            xRight = xLeft + bodyWidth
            xMid = (xLeft + xRight) * 0.5

            isBullish = candle.close >= candle.open
            color = colorBull if isBullish else colorBear

            # Wick
            drawList.add_line(xMid, y_of(candle.high), xMid, y_of(candle.low), color, 1.0)

            # Body
            if isBullish:
                bodyTop, bodyBottom = y_of(candle.close), y_of(candle.open)
            else:
                bodyTop, bodyBottom = y_of(candle.open), y_of(candle.close)
            if abs(bodyBottom - bodyTop) < 1:
                bodyBottom = bodyTop + 1

            drawList.add_rect_filled(xLeft, bodyTop, xRight, bodyBottom, color)

        # Time step labels
        timeY = originY + chartHeight + 4

        # Time steps being shown
        firstTick = int(candles[0].startTime)
        lastTick = int(candles[-1].startTime) + self.timeframe
        tickSpan = lastTick - firstTick
        if tickSpan <= 0:
            tickSpan = 1

        rawStep = tickSpan / 5
        tickStep = max(100, int(math.ceil(rawStep / 100) * 100))

        firstLabel = int(math.ceil(firstTick / tickStep) * tickStep)

        tick = firstLabel
        while tick <= lastTick:
            fraction = (tick - firstTick) / (lastTick - firstTick) if lastTick != firstTick else 0
            x = originX + fraction * chartWidth
            if originX <= x <= originX + chartWidth:
                label = str(tick)
                textWidth = len(label) * 3.5
                drawList.add_text(x - textWidth, timeY, colorLabel, label)
            tick += tickStep

    def _drawLine(self, candles):
        drawList = imgui.get_window_draw_list()

        avail = imgui.get_content_region_available()
        marginRight = 70
        marginBottom = 24
        chartWidth = avail.x - marginRight
        chartHeight = avail.y - 30 - marginBottom

        origin = imgui.get_cursor_screen_position()
        originX, originY = origin.x, origin.y
        imgui.invisible_button("##chart_line", avail.x, avail.y - 30)

        # Price range
        rawMin = min(c.low for c in candles)
        rawMax = max(c.high for c in candles)
        priceMin = math.floor(rawMin * 0.95 / 10) * 10
        priceMax = math.ceil(rawMax * 1.05 / 10) * 10
        priceRange = priceMax - priceMin if priceMax != priceMin else 1.0

        def y_of(price):
            return originY + chartHeight - ((price - priceMin) / priceRange) * chartHeight

        numCandles = len(candles)
        totalWidth = chartWidth / max(numCandles, 1)

        colorLabel = imgui.get_color_u32_rgba(0.70, 0.70, 0.70, 1.0)
        colorBg = imgui.get_color_u32_rgba(0.10, 0.10, 0.12, 1.0)
        colorLine = imgui.get_color_u32_rgba(0.30, 0.60, 1.00, 1.0)

        drawList.add_rect_filled(originX, originY, originX + chartWidth, originY + chartHeight, colorBg)

        # Price labels
        priceStep = 5
        firstLevel = int(priceMin / priceStep) * priceStep
        if firstLevel < priceMin:
            firstLevel += priceStep
        level = firstLevel
        while level <= priceMax:
            labelY = y_of(level)
            drawList.add_text(originX + chartWidth + 6, labelY - 7, colorLabel, f"{level:.2f}")
            level += priceStep

        # Line segments between close prices
        for i in range(numCandles - 1):
            x1 = originX + (i + 0.5) * totalWidth
            x2 = originX + (i + 1.5) * totalWidth
            y1 = y_of(candles[i].close)
            y2 = y_of(candles[i + 1].close)
            drawList.add_line(x1, y1, x2, y2, colorLine, 2.0)

        # Time step labels
        timeY = originY + chartHeight + 4
        firstTick = int(candles[0].startTime)
        lastTick = int(candles[-1].startTime) + self.timeframe
        tickSpan = lastTick - firstTick
        if tickSpan <= 0:
            tickSpan = 1
        rawStep = tickSpan / 5
        tickStep = max(100, int(math.ceil(rawStep / 100) * 100))
        firstLabel = int(math.ceil(firstTick / tickStep) * tickStep)
        tick = firstLabel
        while tick <= lastTick:
            fraction = (tick - firstTick) / (lastTick - firstTick) if lastTick != firstTick else 0
            x = originX + fraction * chartWidth
            if originX <= x <= originX + chartWidth:
                label = str(tick)
                textWidth = len(label) * 3.5
                drawList.add_text(x - textWidth, timeY, colorLabel, label)
            tick += tickStep
