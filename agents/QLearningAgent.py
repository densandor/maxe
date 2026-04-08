from thesimulator import *
import random
import numpy as np


class QLearningAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 10))

        # QLearningAgent-specific parameters
        self.pnlAgent = str(params.get("pnlAgent", "PNL_AGENT")) # PnL manager agent name for checking inventory
        
        # Q-learning parameters
        self.alpha = float(params.get("alpha", 0.03)) # learning rate
        self.gamma = float(params.get("gamma", 0.97)) # discount factor
        self.epsilon = float(params.get("epsilon", 1)) # exploration rate
        self.minEpsilon = float(params.get("minEpsilon", 0.1))
        self.epsilonDecay = float(params.get("epsilonDecay", 0.995))

        # State space
        self.numTrends = 7 # discretized price trend (0 = no change or insufficient data, 1 = small upward trend, 2 = medium upward trend, 3 = large upward trend, 4 = small downward trend, 5 = medium downward trend, 6 = large downward trend)
        self.numPositions = 3 # discretized position (0 = negative position, 1 = no existing position, 2 = positive position)

        # Action space 
        self.numActions = 5 # (0 =  do nothing, 1 = buy 1 unit, 2 = buy 5 units, 3 = sell 1 unit, 4 = sell 5 units)

        # Q-table
        self.Q = np.zeros((self.numTrends * self.numPositions, self.numActions))
        self.previousState = None
        self.previousAction = None

        self.oldPrice = None # last trade price seen
        self.oldPnl = 0

        self.trend = 0 # placeholder for current trend

    # Helper methods for state and encoding
    def _discretizePosition(self, position):
        if position < 0:
            return 0
        elif position > 0:
            return 1
        else:
            return 2

    def _discretiseTrend(self, oldPrice, currentPrice, threshold=0.01):
        if oldPrice is None or oldPrice == 0 or currentPrice == oldPrice:
            return 0
        relativeChange = (currentPrice - oldPrice) / oldPrice
        if relativeChange > 2 * threshold:
            return 3  # Large upward
        elif relativeChange > threshold:
            return 2  # Medium upward
        elif relativeChange > 0:
            return 1  # Small upward
        elif relativeChange >= -threshold:
            return 4  # Small downward
        elif relativeChange >= -2 * threshold:
            return 5  # Medium downward
        else:
            return 6  # Large downward

    def _stateToIndex(self, position, trend):
        positionIndex = self._discretizePosition(position)
        return positionIndex * 7 + trend

    def _epsilonGreedy(self, stateIndex):
        if random.random() < self.epsilon:
            # Explore with random action with probability epsilon
            action = random.choice(range(self.numActions))
            return action
        else:
            # Exploit best known action with probability 1 - epsilon
            action = int(np.argmax(self.Q[stateIndex, :]))
            return action
    
    # Q-learning update
    def _updateQ(self, reward, newStateIndex):
        if self.previousState is None or self.previousAction is None:
            return
        s = self.previousState
        a = self.previousAction
        bestNextReward = np.max(self.Q[newStateIndex, :])
        self.Q[s, a] = (1 - self.alpha) * self.Q[s, a] + self.alpha * (reward + self.gamma * bestNextReward)

    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            # Schedule first wake-up
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return

        if type == "WAKE_UP":
            # Schedule next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            # Request L1 data from the exchange
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
            return

        if type == "RESPONSE_RETRIEVE_L1":
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            currentPrice = float(payload.lastTradePrice.toCentString())

            if currentPrice <= 0 or (bestAsk <= 0 and bestBid <= 0):
                return

            # Compute simple trend and store it for when PnL response arrives (since we need to wait for PnL response to do the Q-learning update)
            self.trend = self._discretiseTrend(self.oldPrice, currentPrice)
            self.oldPrice = currentPrice

            # Request PnL snapshot from PnL manager and wait for RESPONSE_PNL
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnlAgent, "REQUEST_PNL", EmptyPayload())
            return

        if type == "RESPONSE_PNL":
            # Received PnL response from PnLManagerAgent
            realized = payload.realizedPnl
            unrealized = payload.unrealizedPnl
            inventory = payload.inventory

            # Current state index
            stateIndex = self._stateToIndex(inventory, self.trend)

            # Calculate reward as change in total PnL since last update
            totalPnl = realized + unrealized
            reward = totalPnl - self.oldPnl
            self.oldPnl = totalPnl

            # Update Q-table
            if self.previousState is not None and self.previousAction is not None:
                self._updateQ(reward, stateIndex)

            # Choose new action
            action = self._epsilonGreedy(stateIndex)

            # Store previous state/action for next update
            self.previousState = stateIndex
            self.previousAction = action

            # Decay epsilon
            if self.epsilon > self.minEpsilon:
                self.epsilon *= self.epsilonDecay

            # Execute action
            if action == 0:  # Do Nothing
                pass
            elif action == 1:  # Buy 1
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Buy, 1))
            elif action == 2:  # Buy 5
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Buy, 5))
            elif action == 3:  # Sell 1
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Sell, 1))
            elif action == 4:  # Sell 5
                simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(OrderDirection.Sell, 5))
            return
