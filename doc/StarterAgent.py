from thesimulator import *
import random

class StarterAgent:
    def configure(self, params):
        # save locally the configuration params passed so that they are properly typed
        self.exchange = str(params['exchange'])
        self.price = float(params['price'])
        self.p_buy = float(params['p_buy'])
        self.quantity = int(params['quantity'])
    
    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            sellPrice = Money(self.price * 1.01)
            buyPrice = Money(self.price * 0.99)

            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Buy, self.quantity, buyPrice))

            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Sell, self.quantity, sellPrice))
            return
    