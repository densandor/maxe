from thesimulator import *
import random
import math

class FundamentalAgent:
    """
    Fundamental trader

    At each wake-up, the agent updates its believed fundamental price by adding Gaussian noise (N(0, update_s_d)), then compares that fundamental to the current best ask/bid to compute mispricing and demand d = sensitivity * mispricing.
    If |d| >= 1 the agent places a market order with volume = round(|d|) (clipped to [1, max_volume]) and side determined by sign(d).
    """
    def configure(self, params):

        # Generic parameters
        self.exchange = str(params["exchange"])
        self.interval = int(params["interval"])
        self.offset = int(params.get("offset", 1))
        self.trade_probability = float(params.get("trade_probability", 0.1))

        # FundamentalAgent-specific parameters
        self.fundamental_price = float(params.get("fundamental_price_init", 100.0)) # the price the agent believes the asset to be worth
        self.sensitivity = float(params.get("sensitivity", 0.001)) # how sensitive demand is to mispricing
        self.update_s_d = float(params.get("update_s_d", 10.0)) # the standard deviation for random updates to fundamental price
        self.max_volume = int(params.get("max_volume", 10)) # limits on volume

    # Fundamental price update (simulates random information coming in)
    def _update_fundamental_price(self):
        self.fundamental_price += random.gauss(0.0, self.update_s_d)

    # Message handling
    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()
        
        if type == "EVENT_SIMULATION_START":
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return

        if type == "WAKE_UP":
            # Update fundamental_price
            self._update_fundamental_price()
            # Schedule next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())

            # Decide whether to attempt a trade this wakeup (probabilistic trading)
            if random.random() >= self.trade_probability:
                return

            # Request L1 data from the exchange (only if we intend to trade)
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
            return

        if type == "RESPONSE_RETRIEVE_L1":
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())

            current_fundamental_price = self.fundamental_price
            # If there are no resting orders, do nothing
            if bestAsk <= 0 and bestBid <= 0:
                return

            # Demand function (buy / sell / idle)
            if bestAsk > 0 and current_fundamental_price > bestAsk:
                mispricing = current_fundamental_price - bestAsk
                raw_demand = self.sensitivity * mispricing
                volume = int(max(1, min(self.max_volume, math.floor(raw_demand))))
                direction = OrderDirection.Buy
            elif bestBid > 0 and current_fundamental_price < bestBid:
                mispricing = bestBid - current_fundamental_price
                raw_demand = self.sensitivity * mispricing
                volume = int(max(1, min(self.max_volume, math.floor(raw_demand))))
                direction = OrderDirection.Sell
            else:
                return

            if volume <= 0:
                return

            # Place market order
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))
            return
