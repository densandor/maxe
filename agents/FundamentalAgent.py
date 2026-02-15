from thesimulator import *
import random
from numpy import random as np_random


class FundamentalAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
        self.pTrade = float(params.get("pTrade", 0.15))

        # FundamentalAgent-specific parameters
        self.newsAgent = str(params.get("newsAgent", "NEWS_AGENT")) # News agent
        self.fundamentalPrice = float(params.get("fundamentalPrice", random.uniform(20, 25))) # the price the agent believes the asset to be worth
        
        self.recentNews = None
        self.priceUpdateSigma = float(params.get("priceUpdateSigma", 0.2)) # the standard deviation for random updates to fundamental price

        self.marketOrderThreshold = float(params.get("marketOrderThreshold", random.uniform(0.005, 0.25))) # the minimum mispricing required to place a market order
        self.opinionThreshold = float(params.get("opinionThreshold", random.uniform(0.01, 0.1))) # the minimum mispricing required to place any order (market or limit)
        self.limitOrderLambda = float(params.get("limitOrderLambda", 3)) # the lambda parameter for the exponential distribution used to determine limit order prices

    # Fundamental price update
    def _update_fundamentalPrice(self):
        self.fundamentalPrice += random.gauss(self.recentNews, self.priceUpdateSigma)

    # Message handling
    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()
        
        if type == "EVENT_SIMULATION_START":
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.newsAgent, "SUBSCRIBE_NEWS", EmptyPayload())
            return

        if type == "WAKE_UP":
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
            if bestAsk > 0 and bestBid > 0:
                midPrice = (bestAsk + bestBid) / 2
            else:
                midPrice = self.fundamentalPrice

            if abs(1 - self.fundamentalPrice / midPrice) > self.opinionThreshold:
                if self.fundamentalPrice >= midPrice:
                    self.fundamentalPrice = midPrice * (1 + self.opinionThreshold)
                else:
                    self.fundamentalPrice = midPrice * (1 - self.opinionThreshold)

            currentFundamentalPrice = self.fundamentalPrice

            # Sample from symmetric exponential distribution centered at midPrice
            exp_sample = np_random.exponential(scale=1.0/self.limitOrderLambda)
            sign = np_random.choice([-1, 1])
            plannedPrice = midPrice + sign * exp_sample
            # print("[{}] Current fundamental price: {}, best bid: {}, best ask: {}, planned order price: {}".format(self.name(),currentFundamentalPrice, bestBid, bestAsk, plannedPrice))
            plannedPrice = Money(round(plannedPrice, 2))

            if bestAsk > 0 and currentFundamentalPrice > bestAsk * (1 + self.marketOrderThreshold):
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Buy, 1))
                # plannedPrice = Money(round(bestAsk * (1 + self.marketOrderThreshold) * 1.05, 2))
                # simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Buy, 1, plannedPrice))
            elif bestBid > 0 and currentFundamentalPrice < bestBid * (1 - self.marketOrderThreshold):
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Sell, 1))
                # plannedPrice = Money(round(bestBid * (1 - self.marketOrderThreshold) * 0.95, 2))
                # simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Sell, 1, plannedPrice))
            elif bestAsk > 0 and currentFundamentalPrice > bestAsk:
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Buy, 1, plannedPrice))
            elif bestBid > 0 and currentFundamentalPrice < bestBid:
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Sell, 1, plannedPrice))
            elif bestAsk == 0 and bestBid == 0:
                if currentFundamentalPrice > midPrice:
                    simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Buy, 1, plannedPrice))
                else:
                    simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Sell, 1, plannedPrice))
            return
        
        if type == "NEWS":
            self.recentNews = payload.news
            self._update_fundamentalPrice()
            return
