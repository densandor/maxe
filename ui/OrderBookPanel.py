import imgui


class OrderBookPanel:
    def __init__(self, simManager, orderBookQueue):
        self.simManager = simManager
        self.orderBookQueue = orderBookQueue
        self.asks = {}
        self.bids = {}

    def clear(self):
        self.asks.clear()
        self.bids.clear()

    def _drainUpdates(self):
        while len(self.orderBookQueue) > 0:
            try:
                msg = self.orderBookQueue.popleft()
            except IndexError:
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

    def _drawRows(self, levels, side):
        if side == "B":
            priceColor = (0.44, 0.95, 0.76)
        else:
            priceColor = (0.95, 0.53, 0.53)

        textColor = (0.78, 0.82, 0.90)

        flags = imgui.TABLE_SIZING_STRETCH_PROP | imgui.TABLE_ROW_BACKGROUND
        if imgui.begin_table(f"ob_{side}_table", 3, flags):
            imgui.table_setup_column("Price")
            imgui.table_setup_column("Size")
            imgui.table_setup_column("Depth")
            imgui.table_headers_row()

            askDepths = None
            if side == "A":
                askDepths = [0.0] * len(levels)
                running = 0.0
                for i in range(len(levels) - 1, -1, -1):
                    running += levels[i][1]
                    askDepths[i] = running

            runningDepth = 0.0
            for idx, (price, qty) in enumerate(levels):
                if side == "A":
                    depthValue = askDepths[idx]
                else:
                    runningDepth += qty
                    depthValue = runningDepth

                imgui.table_next_row()

                imgui.table_set_column_index(0)
                imgui.text_colored(f"{price:.2f}", *priceColor)

                imgui.table_set_column_index(1)
                imgui.text_colored(f"{qty:.1f}", *textColor)

                imgui.table_set_column_index(2)
                imgui.text_colored(f"{depthValue:.1f}", *textColor)

            imgui.end_table()

    def render(self):
        self._drainUpdates()

        imgui.set_next_window_position(1600, 0, imgui.ONCE)
        imgui.set_next_window_size(320, 720, imgui.ONCE)

        if imgui.begin("Order Book"):
            nearestAsks = sorted(self.asks.items(), key=lambda x: x[0])[:15]
            asks = list(reversed(nearestAsks))
            bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:15]
            totalAskVolume = sum(self.asks.values())
            totalBidVolume = sum(self.bids.values())

            topH = 300
            midH = 50
            footerH = 20

            imgui.begin_child("##asks", width=0, height=topH, border=True)
            self._drawRows(asks, "A")
            imgui.end_child()

            imgui.begin_child("##mid", width=0, height=midH, border=True)
            latest = self.simManager.latestTradePrice
            spread = None
            if self.asks and self.bids:
                spread = min(self.asks.keys()) - max(self.bids.keys())
            if latest is not None:
                imgui.set_cursor_pos_x(max(0, (imgui.get_window_width() - imgui.calc_text_size(f"${latest:.2f}").x) * 0.5))
                imgui.text_colored(f"${latest:.2f}", 0.44, 0.95, 0.76)
                if spread is not None:
                    spreadText = f"Spread: {spread:.2f}"
                    imgui.set_cursor_pos_x(max(0, (imgui.get_window_width() - imgui.calc_text_size(spreadText).x) * 0.5))
                    imgui.text(spreadText)
            else:
                imgui.text("Waiting for trade price...")
            imgui.end_child()

            imgui.begin_child("##bids", width=0, height=topH, border=True)
            self._drawRows(bids, "B")
            imgui.end_child()

            imgui.begin_child("##book_totals", width=0, height=footerH, border=False)
            imgui.text_colored(f"Ask Vol: {totalAskVolume:.1f}", 0.95, 0.53, 0.53)
            imgui.same_line()
            label = f"Bid Vol: {totalBidVolume:.1f}"
            labelWidth = imgui.calc_text_size(label).x
            x = max(0.0, imgui.get_window_width() - labelWidth - 10)
            imgui.set_cursor_pos_x(x)
            imgui.text_colored(label, 0.44, 0.95, 0.76)
            imgui.end_child()

            imgui.end()
