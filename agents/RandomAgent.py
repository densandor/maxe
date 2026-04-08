from thesimulator import *
import random


class RandomAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
        self.pTrade = float(params.get("pTrade", random.uniform(0.2, 0.4)))

        # RandomAgent-specific parameters
        self.maxVolume = int(params.get("maxVolume", 5))

    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()
    
        if type == "EVENT_SIMULATION_START":
            # Schedule the first wakeup
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return
        if type == "WAKE_UP":
            # Schedule the next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            # Decide whether to submit an order this wakeup
            if random.random() >= self.pTrade:
                return
            # Request L1 data from the exchange
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
            return
        if type == "RESPONSE_RETRIEVE_L1":
            
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            # Choose side
            if random.random() < 0.5:
                direction = OrderDirection.Buy
            else:
                direction = OrderDirection.Sell

            # Up to 1% away from last trade price
            delta = random.uniform(0.0, 0.01)

            # Inefficient limit order (simulates a market order but only within detla of last trade price)
            if direction == OrderDirection.Buy:
                plannedPrice = lastTradePrice * (1.0 + abs(delta))
            else:
                plannedPrice = lastTradePrice * (1.0 - abs(delta))

            volume  = random.randint(1, self.maxVolume)

            plannedPrice = max(plannedPrice, 0.01) # Ensure price is positive
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, volume, Money(plannedPrice)))
            return
