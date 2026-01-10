from thesimulator import *
import random
import math

class FundamentalAgent:
    def configure(self, params):

        # Generic parameters
        self.exchange = str(params["exchange"])
        self.interval = int(params["interval"])
        self.offset = int(params.get("offset", 1))

        # FundamentalAgent-specific parameters
        self.fundamental_price = float(params.get("fundamental_price_init", 10000.0))
        self.sensitivity = float(params.get("sensitivity", 0.001))
        self.update_s_d = float(params.get("update_s_d", 10.0))
        self.max_volume = int(params.get("max_volume", 10))

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
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            # Request L1 data from the exchange
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", RetrieveL1Payload())
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
