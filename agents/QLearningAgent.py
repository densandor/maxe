from thesimulator import *
import random
import numpy as np

class QLearningAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))

        # QLearningAgent-specific parameters
        self.pnlAgent = str(params.get("pnlAgent", "PNL_AGENT")) # PnL manager agent name for checking inventory
        
        # Q-learning parameters
        self.alpha = float(params.get("alpha", 0.1)) # learning rate
        self.gamma = float(params.get("gamma", 0.99)) # discount factor
        self.epsilon = float(params.get("epsilon", 1)) # exploration rate
        self.minEpsilon = float(params.get("minEpsilon", 0.01))
        self.epsilonDecay = float(params.get("epsilonDecay", 0.995))

        # State space: (positionIndex * 3 + trendIndex) in [0, 8]
        self.positions = [-1, 0, 1]
        self.trends = [-1, 0, 1]

        # Action space: 0 = go short 1, 1 = go flat, 2 = go long 1
        self.actionSpace = [0, 1, 2]

        # Q-table: 9 states x 3 actions
        self.Q = np.zeros((len(self.positions) * len(self.trends), len(self.actionSpace)))
        self.previousState = None
        self.previousAction = None

        # Book-keeping
        self.position = 0 # current signed position (−1, 0, +1)
        self.oldPrice = None # last trade price seen
        self.oldPnl = 0

        self.pendingState = None # placeholder for pending state when awaiting PnL response

    # Helper methods for state and action encoding
    def _discretiseTrend(self, oldPrice, currentPrice, threshold=0.0001):
        if oldPrice is None or oldPrice <= 0:
            return 0
        relativeChange = (currentPrice - oldPrice) / oldPrice
        if relativeChange > threshold:
            return 1
        elif relativeChange < -threshold:
            return -1
        else:
            return 0

    def _stateToIndex(self, position, trend):
        positionIndex = self.positions.index(position)
        trendIndex = self.trends.index(trend)
        return positionIndex * len(self.trends) + trendIndex

    def _epsilonGreedy(self, stateIndex):
        if random.random() < self.epsilon:
            return random.choice(self.actionSpace) # explore with random action with probability epsilon
        else:
            return int(np.argmax(self.Q[stateIndex, :])) # exploit best known action with probability 1 - epsilon
    
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

            # Compute simple trend
            trend = self._discretiseTrend(self.oldPrice, currentPrice)
            self.oldPrice = currentPrice

            # Current state index
            stateIndex = self._stateToIndex(self.position, trend)

            # Store pending state for continuation when RESPONSE_PNL arrives
            self.pendingState = stateIndex
            # Request PnL snapshot from PnL manager and wait for RESPONSE_PNL
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnlAgent, "REQUEST_PNL", EmptyPayload())
            return

        if type == "RESPONSE_PNL":
            # Received PnL response from PnLManagerAgent
            realized = payload.realizedPnl
            unrealized = payload.unrealizedPnl

            totalPnl = realized + unrealized
            reward = totalPnl - self.oldPnl
            self.oldPnl = totalPnl

            # Continue Q-learning update using pending state
            if self.pendingState is None:
                return
            stateIndex = self.pendingState
            self.pendingState = None

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

            # Translate action to target position
            targetPosition = self.positions[action]

            # Decide order direction and volume to move from current position to target
            positionChange = targetPosition - self.position
            if positionChange == 0:
                return
            
            if positionChange > 0:
                direction = OrderDirection.Buy
            else:
                direction = OrderDirection.Sell
            volume = abs(positionChange)

            # Place market order to change position
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))
            return
