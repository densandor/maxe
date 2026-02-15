from thesimulator import *
import random
import math


class MAOAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))

        # MomentumAgent-specific parameters
        self.pnlAgent = str(params.get("pnlAgent", "PNL_AGENT"))
        self.marketDataAgent = str(params.get("marketDataAgent", "MARKET_DATA_AGENT")) # Market data agent name for checking moving average signals

        self.profitFactor = float(params.get("profitFactor", 0.01)) # factor for taking profits
        self.waitTime = int(params.get("waitTime", random.uniform(0, 50))) # time to wait before acting on a moving average signal, in number of simulation steps

        self.lastTradePrice = None

    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            # Subscribe to moving average signals from the market data agent
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.marketDataAgent, "SUBSCRIBE_MOVING_AVERAGE", EmptyPayload())
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
            self.lastTradePrice = float(payload.lastTradePrice.toCentString())
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnlAgent, "REQUEST_PNL", EmptyPayload())
            return

        if type == "RESPONSE_PNL":
            inventory = payload.inventory
            avgPrice = float(payload.avgPrice)

            if inventory > 0:
                profitTargetPrice = avgPrice * (1 + self.profitFactor)
            elif inventory < 0:
                profitTargetPrice = avgPrice * (1 - self.profitFactor)
            
            if inventory > 0 and self.lastTradePrice > profitTargetPrice:
                # print("Taking profit on long position: inventory={}, avgPrice={}, currentPrice={}, targetPrice={}".format(inventory, avgPrice, self.lastTradePrice, profitTargetPrice))
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Sell, math.floor(abs(inventory))))
                # simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Sell, math.floor(abs(inventory)), Money(round(profitTargetPrice * 0.95, 2))))
            if inventory < 0 and self.lastTradePrice < profitTargetPrice:
                # print("Taking profit on short position: inventory={}, avgPrice={}, currentPrice={}, targetPrice={}".format(inventory, avgPrice, self.lastTradePrice, profitTargetPrice))
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Buy, math.floor(abs(inventory))))
                # simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Buy, math.floor(abs(inventory)), Money(round(profitTargetPrice * 1.05, 2))))
            return
        
        if type == "MOVING_AVERAGE_SIGNAL":
            direction = payload.direction
            # if direction == OrderDirection.Buy:
            #     plannedPrice = float(payload.price.toCentString()) * 1.05
            # else:
            #     plannedPrice = float(payload.price.toCentString()) * 0.95
            simulation.dispatchMessage(currentTimestamp, self.waitTime, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, 1))
            # simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(direction, 1, Money(round(plannedPrice, 2))))
            return
        
        # if type == "RESPONSE_PLACE_ORDER_LIMIT":
        #     orderID = payload.id
        #     simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "SUBSCRIBE_EVENT_ORDER_TRADE", SubscribeEventTradeByOrderPayload(orderID))
        #     return

        # if type == "EVENT_TRADE":
        #     return