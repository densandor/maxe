from thesimulator import *
import collections
import random
import math

class MomentumAgent:
    """
    Momentum trader

    1. At each wake-up the agent requests L1 data and updates a short history of trade prices.
    2. It computes the relative price change over `lookback` periods.
    3. If the change exceeds `threshold` it places a market order to buy (or to sell if the change is below -`threshold`).
    4. Orders use the configured `sensitivity`.
    """

    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
        self.pTrade = float(params.get("pTrade", 0.2))

        # MomentumAgent-specific parameters
        self.pnlAgent = str(params.get("pnlAgent", "PNL")) # PnL manager agent name for checking inventory

        self.lookback = int(params.get("lookback", 5)) # how many past prices to use
        self.threshold = float(params.get("threshold", 0.001)) # minimum return to act (e.g. 0.1%)
        self.priceHistory = collections.deque(maxlen=self.lookback) # local price history

        self.sensitivity = int(params.get("sensitivity", 1)) # base order sensitivity
        self.maxInventory = int(params.get("maxInventory", 50)) # maximum inventory (absolute) before scaling orders down
        self.slowdownExponent = float(params.get("slowdownExponent", 1)) # how quickly to scale down orders near max inventory

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
            
            # Decide whether to attempt a trade this wakeup (needs to be done after updating prices)
            if random.random() >= self.pTrade:
                return

            # Compare latest price to older price
            currentPrice = self.priceHistory[-1]
            oldPrice = self.priceHistory[0]
            self.relativeChange = (currentPrice - oldPrice) / oldPrice  # positive = uptrend, negative = downtrend

            # Decide direction based on momentum and threshold
            if self.relativeChange > self.threshold:
                direction = OrderDirection.Buy
            elif self.relativeChange < -self.threshold:
                direction = OrderDirection.Sell
            else:
                return

            # Query PnL manager for inventory before placing the order so we can scale size
            self.pendingOrderDirection = direction
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnlAgent, "REQUEST_PNL", EmptyPayload())
            return

        if type == "RESPONSE_PNL":
            # Place pending order adjusted by current inventory
            if self.pendingOrderDirection is None:
                return
            inventory = payload.inventory
            direction = self.pendingOrderDirection
            self.pendingOrderDirection = None

            # Reducer the order size as inventory approaches limit
            if self.maxInventory <= 0:
                scale = 1.0
            else:
                scale = max(0.0, 1.0 - (abs(inventory) / float(self.maxInventory))**self.slowdownExponent)

            volume = int(math.floor(self.relativeChange * self.sensitivity * scale))

            if volume <= 0:
                return

            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))
            return
