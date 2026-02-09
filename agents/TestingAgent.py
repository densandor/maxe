from thesimulator import *
import random

class TestingAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))

        # TestingAgent-specific parameters
        self.direction = OrderDirection.Buy if params.get("direction", "buy").lower() == "buy" else OrderDirection.Sell
        self.volume = int(params.get("volume", 1))
        self.delta = int(params.get("delta", 0))

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
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            price = lastTradePrice + self.delta if self.direction == OrderDirection.Buy else lastTradePrice - self.delta

            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(self.direction, self.volume, Money(price)))
            # print(f"{self.name()} placed a limit order: direction={self.direction}, volume={self.volume}, price={price}")
            return
