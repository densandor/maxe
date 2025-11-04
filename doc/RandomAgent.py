from thesimulator import *
import random

class RandomAgent:
    def configure(self, params):
        # save locally the configuration params passed so that they are properly typed
        self.exchange = str(params['exchange'])
        self.p_buy = float(params['p_buy'])
        self.quantity = int(params['quantity'])
        self.interval = int(params['interval'])
        
    
    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            print("%s:  Starting" % (self.name()))
            # Schedule the first wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return
        if type == "WAKE_UP":
            print("%s:  Waking up & requesting L1 data" % (self.name()))
            # Schedule the next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            # Request L1 data from the exchange
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
            return
        if type == "RESPONSE_RETRIEVE_L1":
            print("%s:  Received L1 data" % (self.name()))
            # payload.bestAskPrice and payload.bestBidPrice are Money objects
            bestAsk = getattr(payload, 'bestAskPrice', None)
            bestBid = getattr(payload, 'bestBidPrice', None)

            # choose side 50/50
            if random.random() < 0.5:
                print("%s:  Buying" % (self.name()))
                direction = OrderDirection.Buy
                # if no best ask available, place market order
                if bestAsk is None:
                    print("%s:  No best bid" % (self.name()))
                    simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, self.quantity))
                    return

                # random price up to 1% from best ask
                u = random.uniform(-1,1) * 0.01
                planned_price = bestAsk * (1.0 + u)

                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, self.quantity, planned_price))
            else:
                print("%s:  Selling" % (self.name()))
                direction = OrderDirection.Sell
                # if no best bid available, place market order
                if bestBid is None:
                    print("%s:  No best bid" % (self.name()))
                    simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, self.quantity))
                    return

                # random price up to 1% away from best bid
                u = random.uniform(-1,1) * 0.01
                planned_price = bestBid * (1.0 + u)

                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, self.quantity, planned_price))
            return
    