from thesimulator import *
import random

class RandomAgent:
    def configure(self, params):
        # save locally the configuration params passed so that they are properly typed
        self.exchange = str(params['exchange'])
        self.p_buy = float(params['p_buy'])
        self.quantity = int(params['quantity'])
        self.interval = int(params['interval'])
        self.offset = int(params.get('offset', 1))

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

            # Choose side 50/50
            if random.random() < self.p_buy:
                direction = OrderDirection.Buy
                # print(f"{self.name()}: BUY", end='')
            else:
                direction = OrderDirection.Sell
                # print(f"{self.name()}: SELL", end='')

            # Choose order type 95% limit, 5% market
            if random.random() < 0.05 and ((direction == OrderDirection.Buy and bestAsk > 0) or (direction == OrderDirection.Sell and bestBid > 0)):
                # print(" MARKET")
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, self.quantity * 100))
            else:
                delta = random.uniform(-1,1) * 0.01
                
                planned_price = lastTradePrice * (1.0 + delta)
                # print(f" (planned: {planned_price:.2f})", end='')
                if direction == OrderDirection.Buy and (planned_price > bestAsk) and bestAsk > 0:
                    planned_price = bestAsk
                    # print(f" new planned: {planned_price:.2f}", end='')
                elif direction == OrderDirection.Sell and (planned_price < bestBid) and bestBid > 0:
                    planned_price = bestBid
                    # print(f" new planned: {planned_price:.2f}", end='')
                # print(f" LIMIT @ {planned_price:.2f}")
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, self.quantity, Money(planned_price)))
            return
    