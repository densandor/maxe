import imgui


class Candle:
    def __init__(self, open_price, time_start):
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.time_start = time_start

    def update(self, price):
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price


class ChartPanel:
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.ticks = [] # (time, price) ticks
        self.candles = [] # aggregated Candle objects
        self.timeframe = 60 # seconds per candle
        self._prev_timeframe = 10
        self.max_ticks = 50000
        self.max_visible = 200 # max candles shown at once
        self._dirty = False # flag to re-aggregate
        self.chart_modes = ["Candle", "Line"]
        self.chart_mode_idx = 0   # 0=Candle, 1=Line

    def clear(self):
        self.ticks.clear()
        self.candles.clear()
        self._dirty = False

    def _aggregate_all(self):
        self.candles.clear()
        if not self.ticks:
            return
        current = None
        for t, p in self.ticks:
            bucket = int(t // self.timeframe) * self.timeframe
            if current is None or current.time_start != bucket:
                if current is not None:
                    self.candles.append(current)
                current = Candle(p, bucket)
            else:
                current.update(p)
        if current is not None:
            self.candles.append(current)

    def _process_tick(self, time_sec, price):
        bucket = int(time_sec // self.timeframe) * self.timeframe
        if not self.candles or self.candles[-1].time_start != bucket:
            self.candles.append(Candle(price, bucket))
        else:
            self.candles[-1].update(price)

    def render(self):
        imgui.set_next_window_position(320, 0, imgui.ALWAYS)
        imgui.set_next_window_size(1280, 720, imgui.ALWAYS)

        if imgui.begin("Price Chart"):
            while not self.data_queue.empty():
                try:
                    time_sec, price = self.data_queue.get_nowait()
                    self.ticks.append((time_sec, price))
                    if not self._dirty:
                        self._process_tick(time_sec, price)
                except Exception:
                    break

            # trim stored ticks
            if len(self.ticks) > self.max_ticks:
                self.ticks = self.ticks[-self.max_ticks:]

            # --- timeframe selector + chart mode dropdown ---
            imgui.push_item_width(120)
            changed, new_tf = imgui.input_int("Timeframe (simulation steps)", self.timeframe, 1, 60)
            imgui.pop_item_width()
            if changed:
                new_tf = max(1, new_tf)
                if new_tf != self.timeframe:
                    self.timeframe = new_tf
                    self._dirty = True

            imgui.same_line()
            imgui.push_item_width(90)
            mode_changed, self.chart_mode_idx = imgui.combo("Chart Mode", self.chart_mode_idx, self.chart_modes)
            imgui.pop_item_width()

            if self._dirty:
                self._aggregate_all()
                self._dirty = False

            if self.candles:
                visible = self.candles[-self.max_visible:]
                c = visible[-1]
                current_step = int(self.ticks[-1][0]) if self.ticks else 0
                info = f"Time Step: {current_step:>8d} | Current Price: {c.close:>10.2f}"
                margin_right = 77 
                right_edge = imgui.get_window_width() - margin_right
                text_w = imgui.calc_text_size(info).x
                imgui.same_line(right_edge - text_w)
                imgui.text(info)

            if self.candles:
                if self.chart_mode_idx == 0:
                    self._draw_candles(visible)
                else:
                    self._draw_line(visible)
            else:
                imgui.text("Run a simulation to see the chart.")

            imgui.end()

    # ------------------------------------------------------------------
    # Candlestick drawing
    # ------------------------------------------------------------------

    def _draw_candles(self, candles):
        draw_list = imgui.get_window_draw_list()

        avail = imgui.get_content_region_available()
        margin_right = 70   # space for price axis labels
        margin_bottom = 24  # space for time axis labels
        chart_w = avail.x - margin_right
        chart_h = avail.y - 30 - margin_bottom  # 30 for OHLC text line
        if chart_w < 50 or chart_h < 50:
            return

        origin = imgui.get_cursor_screen_position()
        ox, oy = origin.x, origin.y

        # reserve the full area so imgui knows it is used
        imgui.invisible_button("##chart", avail.x, avail.y - 30)

        # --- price range: floor/ceil to nearest 10 with 5% padding ---
        import math
        raw_min = min(c.low for c in candles)
        raw_max = max(c.high for c in candles)
        p_min = math.floor(raw_min * 0.95 / 10) * 10
        p_max = math.ceil(raw_max * 1.05 / 10) * 10
        p_range = p_max - p_min if p_max != p_min else 1.0

        def y_of(price):
            return oy + chart_h - ((price - p_min) / p_range) * chart_h

        # --- candle geometry ---
        n = len(candles)
        total_w = chart_w / max(n, 1)
        body_w = max(total_w * 0.7, 2)
        gap = (total_w - body_w) / 2

        # colours (RGBA)
        col_bull = imgui.get_color_u32_rgba(0.15, 0.75, 0.35, 1.0)
        col_bear = imgui.get_color_u32_rgba(0.85, 0.22, 0.20, 1.0)
        col_label = imgui.get_color_u32_rgba(0.70, 0.70, 0.70, 1.0)
        col_bg = imgui.get_color_u32_rgba(0.10, 0.10, 0.12, 1.0)

        # background
        draw_list.add_rect_filled(ox, oy, ox + chart_w, oy + chart_h, col_bg)

        # price labels on the RIGHT (step 5, no grid lines)
        price_step = 5
        first_level = int(p_min / price_step) * price_step
        if first_level < p_min:
            first_level += price_step
        level = first_level
        while level <= p_max:
            yy = y_of(level)
            draw_list.add_text(ox + chart_w + 6, yy - 7, col_label, f"{level:.2f}")
            level += price_step

        # each candle
        for i, c in enumerate(candles):
            x_left = ox + gap + i * total_w
            x_right = x_left + body_w
            x_mid = (x_left + x_right) * 0.5

            bull = c.close >= c.open
            col = col_bull if bull else col_bear

            # wick
            draw_list.add_line(x_mid, y_of(c.high), x_mid, y_of(c.low), col, 1.0)

            # body
            if bull:
                bt, bb = y_of(c.close), y_of(c.open)
            else:
                bt, bb = y_of(c.open), y_of(c.close)
            if abs(bb - bt) < 1:
                bb = bt + 1

            draw_list.add_rect_filled(x_left, bt, x_right, bb, col)

        # --- time axis labels at the bottom (tick numbers at ~20% intervals, multiples of 100) ---
        time_y = oy + chart_h + 4

        # tick range covered by visible candles
        first_tick = int(candles[0].time_start)
        last_tick = int(candles[-1].time_start) + self.timeframe
        tick_span = last_tick - first_tick
        if tick_span <= 0:
            tick_span = 1

        # raw 20% step, then round up to nearest 100
        raw_step = tick_span / 5
        tick_step = max(100, int(math.ceil(raw_step / 100) * 100))

        # first label tick: next multiple of tick_step >= first_tick
        first_label = int(math.ceil(first_tick / tick_step) * tick_step)

        tick = first_label
        while tick <= last_tick:
            # map tick to x position via candle index (fractional)
            frac = (tick - first_tick) / (last_tick - first_tick) if last_tick != first_tick else 0
            x = ox + frac * chart_w
            if ox <= x <= ox + chart_w:
                lbl = str(tick)
                text_w = len(lbl) * 3.5
                draw_list.add_text(x - text_w, time_y, col_label, lbl)
            tick += tick_step

    def _draw_line(self, candles):
        """Draw a line chart connecting the close prices of each candle."""
        draw_list = imgui.get_window_draw_list()
        import math

        avail = imgui.get_content_region_available()
        margin_right = 70
        margin_bottom = 24
        chart_w = avail.x - margin_right
        chart_h = avail.y - 30 - margin_bottom
        if chart_w < 50 or chart_h < 50:
            return

        origin = imgui.get_cursor_screen_position()
        ox, oy = origin.x, origin.y
        imgui.invisible_button("##chart_line", avail.x, avail.y - 30)

        # price range
        raw_min = min(c.low for c in candles)
        raw_max = max(c.high for c in candles)
        p_min = math.floor(raw_min * 0.95 / 10) * 10
        p_max = math.ceil(raw_max * 1.05 / 10) * 10
        p_range = p_max - p_min if p_max != p_min else 1.0

        def y_of(price):
            return oy + chart_h - ((price - p_min) / p_range) * chart_h

        n = len(candles)
        total_w = chart_w / max(n, 1)

        col_label = imgui.get_color_u32_rgba(0.70, 0.70, 0.70, 1.0)
        col_bg = imgui.get_color_u32_rgba(0.10, 0.10, 0.12, 1.0)
        col_line = imgui.get_color_u32_rgba(0.30, 0.60, 1.00, 1.0)

        draw_list.add_rect_filled(ox, oy, ox + chart_w, oy + chart_h, col_bg)

        # price labels on the right
        price_step = 5
        first_level = int(p_min / price_step) * price_step
        if first_level < p_min:
            first_level += price_step
        level = first_level
        while level <= p_max:
            yy = y_of(level)
            draw_list.add_text(ox + chart_w + 6, yy - 7, col_label, f"{level:.2f}")
            level += price_step

        # line segments between close prices
        for i in range(n - 1):
            x1 = ox + (i + 0.5) * total_w
            x2 = ox + (i + 1.5) * total_w
            y1 = y_of(candles[i].close)
            y2 = y_of(candles[i + 1].close)
            draw_list.add_line(x1, y1, x2, y2, col_line, 2.0)

        # time axis labels
        time_y = oy + chart_h + 4
        first_tick = int(candles[0].time_start)
        last_tick = int(candles[-1].time_start) + self.timeframe
        tick_span = last_tick - first_tick
        if tick_span <= 0:
            tick_span = 1
        raw_step = tick_span / 5
        tick_step = max(100, int(math.ceil(raw_step / 100) * 100))
        first_label = int(math.ceil(first_tick / tick_step) * tick_step)
        tick = first_label
        while tick <= last_tick:
            frac = (tick - first_tick) / (last_tick - first_tick) if last_tick != first_tick else 0
            x = ox + frac * chart_w
            if ox <= x <= ox + chart_w:
                lbl = str(tick)
                text_w = len(lbl) * 3.5
                draw_list.add_text(x - text_w, time_y, col_label, lbl)
            tick += tick_step
