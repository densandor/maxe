from thesimulator import *
import collections
import random
import math

class MomentumAgent:
    """
    Momentum trader

    At each wake-up the agent requests L1 data and updates a short history of trade prices.
    It computes the relative price change over `lookback` periods.
    If the relative change exceeds `threshold` it places a limit order to buy slightly inside the spread (or to sell if the change is below -`threshold`).
    Orders use the configured `quantity` and are placed to improve fill odds while avoiding crossing the book.
    """

    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.interval = int(params.get("interval", 1000))
        self.offset = int(params.get("offset", 1))
        self.trade_probability = float(params.get("trade_probability", 0.2))

        # MomentumAgent-specific parameters
        self.pnl_agent = str(params.get("pnlAgent", "PNL")) # PnL manager agent name for checking inventory

        self.quantity = int(params.get("quantity", 1))

        self.lookback = int(params.get("lookback", 5)) # how many past prices to use
        self.threshold = float(params.get("threshold", 0.001)) # minimum return to act (e.g. 0.1%)
        self.prices = collections.deque(maxlen=self.lookback) # local price history

        self.max_inventory = int(params.get("max_inventory", 50)) # maximum inventory (absolute) before scaling orders down
        self.slowdown_exponent = float(params.get("slowdown_exponent", 2.0)) # how quickly to scale down orders near max inventory

        self._pending_order = None # pending planned order waiting for PnL response

    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            # Schedule the first wakeup
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return
        
        if type == "WAKE_UP":
            # Schedule the next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())

            # Request L1 data from the exchange
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
            return
        
        if type == "RESPONSE_RETRIEVE_L1":
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            # === Momentum ===

            # Update local price history
            self.prices.append(lastTradePrice)
            # Decide whether to attempt a trade this wakeup (probabilistic trading)
            if random.random() >= self.trade_probability:
                return

            # Simple momentum: compare latest price to older price
            p_now = self.prices[-1]
            p_past = self.prices[0]

            if p_past <= 0:
                return

            rel_change = (p_now - p_past) / p_past  # positive = uptrend, negative = downtrend
            # Decide direction based on momentum and threshold
            if rel_change > self.threshold:
                direction = OrderDirection.Buy
            elif rel_change < -self.threshold:
                direction = OrderDirection.Sell
            else:
                # No strong signal, do nothing
                return

            # Place a limit order slightly inside the spread if possible, otherwise at last trade
            if direction == OrderDirection.Buy:
                if bestAsk > 0:
                    # bid slightly below best ask to improve fill odds but not cross
                    planned_price = bestAsk * 0.999
                elif bestBid > 0:
                    planned_price = bestBid
                else:
                    planned_price = p_now
            else:  # Sell
                if bestBid > 0:
                    # ask slightly above best bid
                    planned_price = bestBid * 1.001
                elif bestAsk > 0:
                    planned_price = bestAsk
                else:
                    planned_price = p_now
            # Query PnL manager for our inventory before placing the order so we can scale size
            self._pending_order = (direction, planned_price)
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnl_agent, "REQUEST_PNL", EmptyPayload())
            return

        if type == "RESPONSE_PNL":
            # Place pending order adjusted by current inventory
            if self._pending_order is None:
                return
            inventory = int(getattr(payload, "inventory", 0))
            direction, planned_price = self._pending_order
            self._pending_order = None

            # scale factor reduces size as inventory approaches limit
            if self.max_inventory <= 0:
                scale = 1.0
            else:
                scale = max(0.0, 1.0 - (abs(inventory) / float(self.max_inventory))**self.slowdown_exponent)

            order_qty = int(math.floor(self.quantity * scale))
            if order_qty <= 0:
                return

            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, order_qty, Money(planned_price)))
            return

