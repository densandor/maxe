from thesimulator import *
import random

class NewRandomAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
        self.pTrade = float(params.get("pTrade", 0.3))

        # NewRandomAgent-specific parameters
        self.pInefficientOrder = float(params.get("pInefficientOrder", 0.05))
        self.volume = int(params.get("volume", 1))
        self.inefficientMultiplier = int(params.get("inefficientMultiplier", 1))

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
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            # Choose side
            if random.random() < 0.5:
                direction = OrderDirection.Buy
            else:
                direction = OrderDirection.Sell

            # Limit order
            delta = random.uniform(-0.1,0.1) # Up to 2% away from last trade price
            planned_price = lastTradePrice * (1.0 + delta)

            if random.random() < self.pInefficientOrder:
                # Make the order inefficient by placing it on the wrong side of the book
                if direction == OrderDirection.Buy:
                    planned_price = lastTradePrice * (1.0 + abs(delta))
                else:
                    planned_price = lastTradePrice * (1.0 - abs(delta))
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, self.volume * self.inefficientMultiplier, Money(planned_price)))
            else:
                if direction == OrderDirection.Buy and (planned_price > bestAsk) and bestAsk > 0:
                    planned_price = bestAsk
                elif direction == OrderDirection.Sell and (planned_price < bestBid) and bestBid > 0:
                    planned_price = bestBid
            
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, self.volume, Money(planned_price)))
            return
