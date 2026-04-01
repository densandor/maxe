import imgui


class OrderBookPanel:
    def __init__(self, sim_manager, order_book_queue):
        self.sim_manager = sim_manager
        self.order_book_queue = order_book_queue
        self.asks = {}  # price -> volume
        self.bids = {}  # price -> volume

    def clear(self):
        self.asks.clear()
        self.bids.clear()

    def _drain_updates(self):
        while not self.order_book_queue.empty():
            try:
                msg = self.order_book_queue.get_nowait()
            except Exception:
                break

            if not msg:
                continue

            if msg[0] == "R":
                self.clear()
                continue

            try:
                _, side, price, qty = msg
            except ValueError:
                continue

            book = self.bids if side == "B" else self.asks if side == "A" else None
            if book is None:
                continue

            if qty <= 0:
                book.pop(price, None)
            else:
                book[price] = qty

    def _draw_rows(self, levels, side):
        if side == "B":
            price_color = (0.44, 0.95, 0.76)
        else:
            price_color = (0.95, 0.53, 0.53)

        text_color = (0.78, 0.82, 0.90)

        flags = imgui.TABLE_SIZING_STRETCH_PROP | imgui.TABLE_ROW_BACKGROUND
        if imgui.begin_table(f"ob_{side}_table", 3, flags):
            imgui.table_setup_column("Price")
            imgui.table_setup_column("Size")
            imgui.table_setup_column("Depth")
            imgui.table_headers_row()

            # For asks, depth should accumulate from the middle upward
            # (lowest ask at bottom has smallest depth).
            ask_depths = None
            if side == "A":
                ask_depths = [0.0] * len(levels)
                running = 0.0
                for i in range(len(levels) - 1, -1, -1):
                    running += levels[i][1]
                    ask_depths[i] = running

            running_depth = 0.0
            for idx, (price, qty) in enumerate(levels):
                if side == "A":
                    depth_value = ask_depths[idx]
                else:
                    running_depth += qty
                    depth_value = running_depth

                imgui.table_next_row()

                imgui.table_set_column_index(0)
                imgui.text_colored(f"{price:.2f}", *price_color)

                imgui.table_set_column_index(1)
                imgui.text_colored(f"{qty:.1f}", *text_color)

                imgui.table_set_column_index(2)
                imgui.text_colored(f"{depth_value:.1f}", *text_color)

            imgui.end_table()

    def render(self):
        self._drain_updates()

        imgui.set_next_window_position(1600, 0, imgui.ALWAYS)
        imgui.set_next_window_size(320, 720, imgui.ALWAYS)

        if imgui.begin("Order Book"):
            # Top table should end at the inside market: lowest ask at the bottom.
            nearest_asks = sorted(self.asks.items(), key=lambda x: x[0])[:12]
            asks = list(reversed(nearest_asks))
            bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:12]
            total_ask_volume = sum(self.asks.values())
            total_bid_volume = sum(self.bids.values())

            top_h = 300
            mid_h = 56
            footer_h = 24

            imgui.begin_child("##asks", width=0, height=top_h, border=True)
            self._draw_rows(asks, "A")
            imgui.end_child()

            imgui.begin_child("##mid", width=0, height=mid_h, border=True)
            latest = self.sim_manager.latest_trade_price
            spread = None
            if self.asks and self.bids:
                spread = min(self.asks.keys()) - max(self.bids.keys())
            if latest is not None:
                imgui.set_cursor_pos_x(max(0, (imgui.get_window_width() - imgui.calc_text_size(f"${latest:.2f}").x) * 0.5))
                imgui.text_colored(f"${latest:.2f}", 0.44, 0.95, 0.76)
                if spread is not None:
                    spread_text = f"Spread: {spread:.2f}"
                    imgui.set_cursor_pos_x(max(0, (imgui.get_window_width() - imgui.calc_text_size(spread_text).x) * 0.5))
                    imgui.text(spread_text)
            else:
                imgui.text("Waiting for trade price...")
            imgui.end_child()

            remaining_h = imgui.get_content_region_available().y
            bids_h = max(80, remaining_h - footer_h)

            imgui.begin_child("##bids", width=0, height=bids_h, border=True)
            self._draw_rows(bids, "B")
            imgui.end_child()

            imgui.begin_child("##book_totals", width=0, height=footer_h, border=False)
            imgui.text_colored(f"Ask Vol: {total_ask_volume:.1f}", 0.95, 0.53, 0.53)
            imgui.same_line()
            label = f"Bid Vol: {total_bid_volume:.1f}"
            label_w = imgui.calc_text_size(label).x
            x = max(0.0, imgui.get_window_width() - label_w - 10)
            imgui.set_cursor_pos_x(x)
            imgui.text_colored(label, 0.44, 0.95, 0.76)
            imgui.end_child()

            imgui.end()
