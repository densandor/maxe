from thesimulator import *
from PnLTracker import PnLTracker
import collections


class MomentumAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.quantity = int(params["quantity"])
        self.interval = int(params["interval"])
        self.offset = int(params.get("offset", 1))

        # Momentum-specific config
        self.lookback = int(params.get("lookback", 5))  # how many past prices to use
        self.threshold = float(params.get("threshold", 0.001))  # minimum return to act (e.g. 0.1%)
        self.max_history = max(self.lookback + 1, 3)

        # Local price history
        self.prices = collections.deque(maxlen=self.max_history)

        # PnL state
        self.pnl = PnLTracker()

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
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", RetrieveL1Payload())
            return
        
        if type == "RESPONSE_RETRIEVE_L1":
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            self.pnl.mark_to_market(lastTradePrice)

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

        if type == "RESPONSE_PLACE_ORDER_LIMIT":
            order_id = payload.id
            sub_payload = SubscribeEventTradeByOrderPayload(order_id)
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "SUBSCRIBE_EVENT_ORDER_TRADE", sub_payload)
            return
        
        if type == "EVENT_TRADE":
            trade = payload.trade

            fill_price = float(trade.price().toCentString())
            fill_volume = int(trade.volume())
            direction = trade.direction()

            self.pnl.update_on_fill(fill_price, fill_volume, direction)
            return
        
        if type == "EVENT_SIMULATION_STOP":
            print(self.name(), self.pnl.snapshot())
            return