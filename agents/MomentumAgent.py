from thesimulator import *
import collections
import random

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
        self.interval = int(params["interval"])
        self.offset = int(params.get("offset", 1))
        self.trade_probability = float(params.get("trade_probability", 0.2))

        self.quantity = int(params["quantity"])

        # MomentumAgent-specific parameters
        self.lookback = int(params.get("lookback", 5)) # how many past prices to use
        self.threshold = float(params.get("threshold", 0.001)) # minimum return to act (e.g. 0.1%)
        self.prices = collections.deque(maxlen=self.lookback) # local price history

    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            # Schedule the first wakeup
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return
        
        if type == "WAKE_UP":
            # Schedule the next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())

            # Decide whether to attempt trading this wakeup (probabilistic)
            if random.random() >= self.trade_probability:
                return

            # Request L1 data from the exchange
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", RetrieveL1Payload())
            return
        
        if type == "RESPONSE_RETRIEVE_L1":
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            # === Momentum ===

            # Update local price history
            if lastTradePrice > 0:
                self.prices.append(lastTradePrice)

            # Need enough history to compute momentum
            if len(self.prices) < self.lookback + 1:
                return

            # Simple momentum: compare latest price to older price
            p_now = self.prices[-1]
            p_past = self.prices[-1 - self.lookback]
            # print("Most recent price:", p_now, "Olderprice:", p_past)

            if p_past <= 0:
                return

            rel_change = (p_now - p_past) / p_past  # positive = uptrend, negative = downtrend
            # print("Relative change:", rel_change)

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
            # print("Taking a trade: Time =", currentTimestamp, "Side =", direction, "Price =", planned_price)
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, self.quantity, Money(planned_price)))
            return

