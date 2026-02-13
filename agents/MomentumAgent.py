from thesimulator import *
import collections
import random
import math


class MomentumAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
        self.pTrade = float(params.get("pTrade", 1))

        # MomentumAgent-specific parameters
        self.pnlAgent = str(params.get("pnlAgent", "PNL")) # PnL manager agent name for checking inventory

        self.lookback = int(params.get("lookback", 5)) # how many past prices to use
        self.threshold = float(params.get("threshold", 0.01)) # minimum return to act (e.g. 0.1%)
        self.priceHistory = collections.deque(maxlen=self.lookback) # local price history

        self.sensitivity = int(params.get("sensitivity", 100)) # base order sensitivity
        self.maxInventory = int(params.get("maxInventory", 50)) # maximum inventory (absolute) before scaling orders down
        self.slowdownExponent = float(params.get("slowdownExponent", 1)) # how quickly to scale down orders near max inventory
        self.profitFactor = float(params.get("profitFactor", 1.2)) # factor for taking profits
        self.profitProportion = float(params.get("profitProportion", 0.8)) # proportion of position to take when taking profits (0-1]

        self.pendingOrderDirection = None # pending planned order direction waiting for PnL response
        self.relativeChange = 0 # last computed relative price change

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

            # Update local price history
            self.priceHistory.append(lastTradePrice)

            # Compare latest price to older price
            currentPrice = self.priceHistory[-1]
            oldPrice = self.priceHistory[0]
            if oldPrice != 0:
                self.relativeChange = (currentPrice - oldPrice) / oldPrice  # positive = uptrend, negative = downtrend
            
            # Decide direction based on momentum and threshold
            if self.relativeChange > self.threshold:
                self.pendingOrderDirection = OrderDirection.Buy
            elif self.relativeChange < -self.threshold:
                self.pendingOrderDirection = OrderDirection.Sell

            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnlAgent, "REQUEST_PNL", EmptyPayload())
            return

        if type == "RESPONSE_PNL":
            inventory = payload.inventory
            avgPrice = float(payload.avgPrice)

            if inventory > 0:
                profitTargetPrice = avgPrice * self.profitFactor
            elif inventory < 0:
                profitTargetPrice = avgPrice / self.profitFactor
            
            if inventory > 0 and self.priceHistory[-1] > profitTargetPrice:
                print("Taking profit on long position: inventory={}, avgPrice={}, currentPrice={}, targetPrice={}".format(inventory, avgPrice, self.priceHistory[-1], profitTargetPrice))
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Sell, math.floor(abs(inventory) * self.profitProportion)))
            if inventory < 0 and self.priceHistory[-1] < profitTargetPrice:
                print("Taking profit on short position: inventory={}, avgPrice={}, currentPrice={}, targetPrice={}".format(inventory, avgPrice, self.priceHistory[-1], profitTargetPrice))
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Buy, math.floor(abs(inventory) * self.profitProportion)))

            # Decide whether to attempt a momentum trade this wakeup
            if self.pendingOrderDirection is None or random.random() >= self.pTrade:
                return
            
            direction = self.pendingOrderDirection
            self.pendingOrderDirection = None
            
            # Only apply scale if order is increasing inventory in the direction we're already holding
            if (inventory > 0 and direction == OrderDirection.Buy) or (inventory < 0 and direction == OrderDirection.Sell):
                scale = max(0.0, 1.0 - (abs(inventory) / float(self.maxInventory))**self.slowdownExponent)
            else:
                scale = 1.0

            volume = int(math.floor(abs(self.relativeChange) * self.sensitivity * scale))

            # Ensure we don't exceed maxInventory in either direction
            if direction == OrderDirection.Buy:
                volume = min(volume, max(0, self.maxInventory - inventory))
            else:  # Sell
                volume = min(volume, max(0, self.maxInventory + inventory))

            if volume <= 0:
                return
            print("Placing momentum order: direction={}, volume={}, inventory={}, relativeChange={:.4f}, scale={:.4f}".format(direction, volume, inventory, self.relativeChange, scale))
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))
            return
