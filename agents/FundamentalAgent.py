from thesimulator import *
import random
import math


class FundamentalAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
        self.pTrade = float(params.get("pTrade", 0.1))

        # FundamentalAgent-specific parameters
        self.fundamentalPrice = float(params.get("fundamentalPrice", 100.0)) # the price the agent believes the asset to be worth
        self.priceUpdateSigma = float(params.get("priceUpdateSigma", 3.0)) # the standard deviation for random updates to fundamental price
        self.sensitivity = float(params.get("sensitivity", 1)) # how sensitive demand is to mispricing
        self.maxVolume = int(params.get("maxVolume", 10)) # limits on volume

    # Fundamental price update
    def _update_fundamentalPrice(self):
        self.fundamentalPrice += random.gauss(0.0, self.priceUpdateSigma)

    # Message handling
    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()
        
        if type == "EVENT_SIMULATION_START":
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return

        if type == "WAKE_UP":
            # Update fundamentalPrice
            self._update_fundamentalPrice()
            # Schedule next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())

            # Decide whether to attempt a trade this wakeup (probabilistic trading)
            if random.random() >= self.pTrade:
                return

            # Request L1 data from the exchange (only if we intend to trade)
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
            return

        if type == "RESPONSE_RETRIEVE_L1":
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())

            currentFundamentalPrice = self.fundamentalPrice
            # If there are no resting orders, do nothing
            if bestAsk <= 0 and bestBid <= 0:
                return

            if bestAsk > 0 and currentFundamentalPrice > bestAsk:
                mispricing = currentFundamentalPrice - bestAsk
                volume = self.sensitivity * mispricing
                volume = int(max(1, min(self.maxVolume, math.floor(volume))))
                direction = OrderDirection.Buy
            elif bestBid > 0 and currentFundamentalPrice < bestBid:
                mispricing = bestBid - currentFundamentalPrice
                volume = self.sensitivity * mispricing
                volume = int(max(1, min(self.maxVolume, math.floor(volume))))
                direction = OrderDirection.Sell
            else:
                return

            if volume <= 0:
                return

            # Place market order
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))
            return
