from thesimulator import *

class PrintingAgent:
    def configure(self, params):
        print(" --- Configuring with the following parameters --- ")
        print(params)
        print(" ------------------------------------------------- ")
        self.exchange = str(params['exchange'])
        self.interval = int(params.get('interval', 1000))
    
    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            simulation.dispatchMessage(simulation.currentTimestamp(), 0, self.name(), self.exchange, "SUBSCRIBE_EVENT_ORDER_LIMIT", EmptyPayload())
            simulation.dispatchMessage(simulation.currentTimestamp(), 0, self.name(), self.exchange, "SUBSCRIBE_EVENT_ORDER_MARKET", EmptyPayload())
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())
        if type == "WAKE_UP":
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
        print("%d Received a message of type '%s' with payload %s " % (currentTimestamp, type, payload))
    