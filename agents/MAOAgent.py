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

        self.profitFactor = float(params.get("profitFactor", random.uniform(0.01, 0.2))) # factor for taking profits random.uniform(0.01, 0.2)
        self.waitTime = int(params.get("waitTime", random.uniform(0, 20))) # time to wait before acting on a moving average signal, in number of simulation steps random.uniform(0, 20)

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

            # Check the price we can take profits at based on our inventory and the last trade price
            if inventory > 0:
                profitTargetPrice = avgPrice * (1 + self.profitFactor)
            elif inventory < 0:
                profitTargetPrice = avgPrice * (1 - self.profitFactor)
            
            # Place market order to take profits if the last trade price has reached our profit target price
            if inventory > 0 and self.lastTradePrice > profitTargetPrice:
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Sell, math.floor(abs(inventory))))
            if inventory < 0 and self.lastTradePrice < profitTargetPrice:
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Buy, math.floor(abs(inventory))))
            return
        
        if type == "MOVING_AVERAGE_SIGNAL":
            # Place a market order in the direction of the moving average signal after waiting for the specified wait time
            direction = payload.direction
            simulation.dispatchMessage(currentTimestamp, self.waitTime, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, 1))
            return
