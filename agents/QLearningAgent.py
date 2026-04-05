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
        self.alpha = float(params.get("alpha", 0.05)) # learning rate
        self.gamma = float(params.get("gamma", 0.99)) # discount factor
        self.epsilon = float(params.get("epsilon", 1)) # exploration rate
        self.minEpsilon = float(params.get("minEpsilon", 0.01))
        self.epsilonDecay = float(params.get("epsilonDecay", 0.995))

        # State space: position discretized to [-1, 0, 1] and trend in [-1, 0, 1]
        # This gives 9 total states (positionIndex * 3 + trendIndex) in [0, 8]
        self.positions = [-1, 0, 1]  # for state encoding only
        self.trends = [-1, 0, 1]

        # Action space: target positions the agent can move to
        # 0 = go short 5, 1 = go short 1, 2 = go flat, 3 = go long 1, 4 = go long 5
        self.targetPositions = [-5, -1, 0, 1, 5]

        # Q-table: 9 states x 5 actions
        self.Q = np.zeros((len(self.positions) * len(self.trends), len(self.targetPositions)))
        self.previousState = None
        self.previousAction = None

        # Book-keeping
        self.position = 0 # current signed position (−1, 0, +1)
        self.oldPrice = None # last trade price seen
        self.oldPnl = 0

        self.pendingState = None # placeholder for pending state when awaiting PnL response

        self.largeMoves = 0 # count how many times the agent makes large moves (5 units)
        self.moves = 0 # count total moves made by the agent
        
        # Tracking exploration vs exploitation
        self.explorationSteps = []  # list of 0s (exploit) and 1s (explore) for each action taken

    # Helper methods for state and action encoding
    def _discretizePosition(self, position):
        """Discretize actual position to state space [-1, 0, 1]"""
        if position < 0:
            return -1
        elif position > 0:
            return 1
        else:
            return 0

    def _discretiseTrend(self, oldPrice, currentPrice, threshold=0.05):
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
        discretizedPos = self._discretizePosition(position)
        positionIndex = self.positions.index(discretizedPos)
        trendIndex = self.trends.index(trend)
        return positionIndex * len(self.trends) + trendIndex

    def _epsilonGreedy(self, stateIndex):
        if random.random() < self.epsilon:
            # explore with random action with probability epsilon
            action = random.choice(range(len(self.targetPositions)))
            return action, 1  # return (action, is_exploration=1)
        else:
            # exploit best known action with probability 1 - epsilon
            action = int(np.argmax(self.Q[stateIndex, :]))
            return action, 0  # return (action, is_exploration=0)
    
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
            action, isExploration = self._epsilonGreedy(stateIndex)
            self.explorationSteps.append(isExploration)

            # Store previous state/action for next update
            self.previousState = stateIndex
            self.previousAction = action

            # Decay epsilon
            if self.epsilon > self.minEpsilon:
                self.epsilon *= self.epsilonDecay

            # Translate action to target position
            targetPosition = self.targetPositions[action]

            # Decide order direction and volume to move from current position to target
            positionChange = targetPosition - self.position
            if positionChange == 0:
                return
            
            if positionChange > 0:
                direction = OrderDirection.Buy
            else:
                direction = OrderDirection.Sell
            volume = abs(positionChange)
            if volume == 5:
                self.largeMoves += 1
            self.moves += 1
            # Place market order to change position
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))
            return
        
        if type == "EVENT_SIMULATION_STOP":
            print(f"QLearningAgent {self.name()} finished with final position {self.position}, total PnL {self.oldPnl}, and made {self.largeMoves} large moves.")
            print(f"QLearningAgent {self.name()} made a total of {self.moves} moves.")
            
            # Save exploration vs exploitation data in bundles of 50 steps
            from pathlib import Path
            explorationDataPath = Path(__file__).parent.parent / "logs" / f"{self.name()}_exploration_data.csv"
            with open(explorationDataPath, "w") as f:
                f.write("step_bundle,exploration_count,exploitation_count\n")
                for i in range(0, len(self.explorationSteps), 50):
                    bundle = self.explorationSteps[i:i+50]
                    explorationCount = sum(bundle)
                    exploitationCount = len(bundle) - explorationCount
                    bundleIndex = i // 50
                    f.write(f"{bundleIndex},{explorationCount},{exploitationCount}\n")
