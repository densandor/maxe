from thesimulator import *
import random

class RandomAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
<<<<<<< HEAD
        self.pTrade = float(params.get("pTrade", 0.3))
=======
        self.pTrade = float(params.get("pTrade", 0.02))
>>>>>>> d1d1a676631596850660ec09985a37a9535ef9b1

        # RandomAgent-specific parameters
        self.pMarketOrder = float(params.get("pMarketOrder", 0.07))
        self.volume = int(params.get("volume", 1))
        self.marketOrderMultiplier = int(params.get("marketOrderMultiplier", 29))

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

            # Choose order type
            if random.random() < self.pMarketOrder and ((direction == OrderDirection.Buy and bestAsk > 0) or (direction == OrderDirection.Sell and bestBid > 0)):
                # Market order
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, self.volume * self.marketOrderMultiplier))
            else:
                # Limit order
                delta = random.uniform(-1,1) # Up to 1% away from last trade price
                planned_price = lastTradePrice * (1.0 + delta * 0.01)

                if direction == OrderDirection.Buy and (planned_price > bestAsk) and bestAsk > 0:
                    planned_price = bestAsk
                elif direction == OrderDirection.Sell and (planned_price < bestBid) and bestBid > 0:
                    planned_price = bestBid
                
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, self.volume, Money(planned_price)))
            return
