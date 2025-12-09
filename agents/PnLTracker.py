class PnLTracker:
    """
    Simple PnL & inventory tracker for agents.

    Usage in an agent:
        from pnl_tracker import PnLTracker

        def configure(...):
            self.pnl = PnLTracker()

        # on fill:
        self.pnl.update_on_fill(fill_price, fill_volume, direction)

        # on new market price:
        self.pnl.mark_to_market(last_trade_price)
    """

    def __init__(self):
        self.inventory = 0          # signed position
        self.avg_price = 0.0        # average entry price of open position
        self.realized_pnl = 0.0     # realized PnL
        self.unrealized_pnl = 0.0   # mark-to-market PnL
        self.total_pnl = 0.0        # realized + unrealized
        self.last_price = 0.0       # last seen market price

    def update_on_fill(self, fill_price, fill_volume, direction):
        """
        Update inventory and realized PnL given a trade fill.

        fill_price : execution price (float)
        fill_volume: positive quantity (int)
        direction  : OrderDirection.Buy or OrderDirection.Sell
        """
        from thesimulator import OrderDirection  # import locally to avoid circulars

        if fill_volume <= 0:
            return

        # Signed quantity change
        dq = fill_volume if direction == OrderDirection.Buy else -fill_volume

        # No existing position -> open new
        if self.inventory == 0:
            self.inventory = dq
            self.avg_price = fill_price
            return

        # Increasing existing position (same side)
        if (self.inventory > 0 and dq > 0) or (self.inventory < 0 and dq < 0):
            new_inventory = self.inventory + dq
            self.avg_price = (
                (self.avg_price * abs(self.inventory) + fill_price * abs(dq))
                / float(abs(new_inventory))
            )
            self.inventory = new_inventory
            return

        # Reducing or flipping position
        closing_qty = min(abs(self.inventory), abs(dq))

        if self.inventory > 0:  # closing long
            pnl_close = closing_qty * (fill_price - self.avg_price)
        else:  # closing short
            pnl_close = closing_qty * (self.avg_price - fill_price)

        self.realized_pnl += pnl_close

        new_inventory = self.inventory + dq

        if new_inventory == 0:
            # Position fully closed
            self.inventory = 0
            self.avg_price = 0.0
        elif (self.inventory > 0 and new_inventory < 0) or (self.inventory < 0 and new_inventory > 0):
            # Flipped side: remaining quantity is new position at fill_price
            self.inventory = new_inventory
            self.avg_price = fill_price
        else:
            # Partially reduced, still same side
            self.inventory = new_inventory
            # avg_price unchanged for remaining position

    def mark_to_market(self, current_price: float):
        """
        Update unrealized and total PnL given a new market price.
        Call this whenever you get a fresh lastTradePrice.
        """
        self.last_price = current_price

        if self.inventory == 0 or current_price <= 0 or self.avg_price <= 0:
            self.unrealized_pnl = 0.0
        else:
            # inventory sign naturally handles long/short
            self.unrealized_pnl = self.inventory * (current_price - self.avg_price)

        self.total_pnl = self.realized_pnl + self.unrealized_pnl

    def snapshot(self):
        """
        Return a dict snapshot of current PnL state (useful for logging).
        """
        return {
            "inventory": self.inventory,
            "avg_price": self.avg_price,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_pnl": self.total_pnl,
            "last_price": self.last_price,
        }
