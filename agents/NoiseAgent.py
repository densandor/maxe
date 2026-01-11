from thesimulator import *
import random

class NoiseAgent:
    """
    Noise trader
    
    At each wake-up, the agent samples epsilon ~ N(0, sigma_noise) and computes demand d = lambda_scale * epsilon.

    If |d| >= 1 the agent places a market order with volume = round(|d_t|) and side determined by sign(d_t).
    """

    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params["interval"])
        self.trade_probability = float(params.get("trade_probability", 0.02))

        # NoiseAgent-specific parameters
        self.noise_s_d = float(params.get("sigma_noise", 1.0)) # standard deviation of noise
        self.demand_multiplier = float(params.get("lambda", params.get("lambda_scale", 1.0))) # scale for the demand
        self.max_volume = int(params.get("max_volume", 100)) # limits on volume
        self.min_volume = int(params.get("min_volume", 1))

    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            # Schedule the first wakeup
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return

        if type == "WAKE_UP":
            # Schedule the next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())

            # Decide whether to trade this wakeup (probabilistic trading)
            if random.random() >= self.trade_probability:
                return

            # Sample noise and compute demand
            epsilon = random.gauss(0.0, self.sigma_noise)
            demand = self.lambda_scale * epsilon
            volume = int(round(abs(demand)))

            # Enforce volume limits
            if volume < self.min_volume:
                return
            if volume > self.max_volume:
                volume = self.max_volume

            # Positive demand means buy, negative means sell
            if demand > 0:
                direction = OrderDirection.Buy
            else:
                direction = OrderDirection.Sell

            # Place market order
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))
            return
