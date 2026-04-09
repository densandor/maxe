from thesimulator import *
from .dqn.Network import Network
from .dqn.ReplayMemory import ReplayMemory

import numpy as np
import collections
import torch
import torch.nn as nn
import torch.optim as optim


class DQLAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
        self.pTrade = float(params.get("pTrade", 1))
        
        # DQKAgent-specific parameters
        self.pnlAgent = str(params.get("pnlAgent", "PNL"))
        
        # DQN hyperparameters
        self.alpha = float(params.get("alpha", 0.01))
        self.gamma = float(params.get("gamma", 0.95))
        self.epsilon = float(params.get("epsilon", 1.0))
        self.minEpsilon = float(params.get("minEpsilon", 0.1))
        self.epsilonDecay = float(params.get("epsilonDecay", 0.995))
        self.batchSize = int(params.get("batchSize", 5))
        self.memoryCapacity = int(params.get("memoryCapacity", 60))
        self.targetNetworkUpdateFrequency = int(params.get("targetNetworkUpdateFrequency", 50))
        
        # State features: 20 normalized prices + position (21-D total)
        self.position = 0
        self.priceHistory = collections.deque(maxlen=20)
        self.normalisedPriceHistory = np.zeros(20, dtype=np.float32)
        self.oldPnl = 0.0

        self.actionSpaceSize = 5 # Actions: (0 = do nothing, 1 = buy 1 unit, 2 = buy 5 units, 3 = sell 1 unit, 4 = sell 5 units)
        
        # Initialise networks
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.qNetwork = Network(21, 5).to(self.device)
        self.targetNetwork = Network(21, 5).to(self.device)
        self.steps = 0
        self.lastState = None
        self.lastAction = None
        # Initialise target with same weights as Q-network
        self.targetNetwork.load_state_dict(self.qNetwork.state_dict())
        self.targetNetwork.eval() # Target network never trains
        
        # Initialise optimiser and loss
        self.optimiser = optim.Adam(self.qNetwork.parameters(), lr=self.alpha)
        self.lossFunction = nn.SmoothL1Loss(beta=1.0)
        
        # Initialise replay buffer
        self.memory = ReplayMemory(capacity=self.memoryCapacity)   

    def _updateState(self, newPrice):
        self.priceHistory.append(newPrice)

        prices = np.array(self.priceHistory, dtype=np.float32)
        if len(prices) == 0:
            self.normalisedPriceHistory = np.zeros(20, dtype=np.float32)
            return

        base = prices[0]
        if base <= 0:
            normalised = np.zeros(len(prices), dtype=np.float32)
        else:
            normalised = np.log(prices / base)
            normalised = np.clip(normalised, -1.0, 1.0)

        padded = np.zeros(20, dtype=np.float32)
        padded[-len(normalised):] = normalised
        self.normalisedPriceHistory = padded

    def _selectAction(self, state):
        if np.random.random() < self.epsilon:
            # Explore: random action
            return np.random.randint(0, self.actionSpaceSize)
        
        # Exploit: greedy action from Q-network
        stateTensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            qValues = self.qNetwork(stateTensor)
            action = qValues.argmax(dim=1).item()
        return action
    
    def _computeTargetQValues(self, rewards, next_states):
        with torch.no_grad():
            # Select best actions using current Q-network
            best_actions = self.qNetwork(next_states).argmax(dim=1)

            # Evaluate selected actions using target network
            targetQValues = self.targetNetwork(next_states)
            targetQNext = targetQValues.gather(1, best_actions.unsqueeze(1)).squeeze(1)
            
            # Compute target Q-values using Bellman equation
            targetQ = rewards + self.gamma * targetQNext
        
        return targetQ
    
    def _trainStep(self):
        # Check if we have enough data
        if len(self.memory) < self.batchSize:
            return None
        
        # Sample batch
        batch = self.memory.sample(self.batchSize)
        states, actions, rewards, next_states = batch
        
        # Forward Pass
        # Compute Q-values for sampled actions
        qValues = self.qNetwork(states)
        qValuesTaken = qValues.gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Compute target Q-values
        targetQ = self._computeTargetQValues(rewards, next_states)
        
        # Loss Computation
        loss = self.lossFunction(qValuesTaken, targetQ)
        
        # Backward Pass
        self.optimiser.zero_grad()
        loss.backward()
        
        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(self.qNetwork.parameters(), max_norm=1.0)
        
        self.optimiser.step()
        
        self.steps += 1
        
        return loss.item()
    
    def _updateTargetNetwork(self):
        self.targetNetwork.load_state_dict(self.qNetwork.state_dict())
    
    def _decayEpsilon(self):
        self.epsilon = max(self.minEpsilon, self.epsilon * self.epsilonDecay)
    
    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()
        
        if type == "EVENT_SIMULATION_START":
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return
        
        if type == "WAKE_UP":
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
            return
        
        if type == "RESPONSE_RETRIEVE_L1":
            lastTradePrice = float(payload.lastTradePrice.toCentString())
            if lastTradePrice <= 0:
                return
            # Update state features
            self._updateState(lastTradePrice)
            
            # Request PnL from PnL manager agent
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnlAgent, "REQUEST_PNL", EmptyPayload())
            return
        
        if type == "RESPONSE_PNL":
            # Extract PnL data from manager
            inventory = payload.inventory
            realizedPnl = payload.realizedPnl
            unrealizedPnl = payload.unrealizedPnl
            
            # Update position from inventory
            self.position = 1 if inventory > 0 else (-1 if inventory < 0 else 0)
            
            # Compute reward as change in total PnL
            totalPnl = realizedPnl + unrealizedPnl
            reward = totalPnl - self.oldPnl
            self.oldPnl = totalPnl
            
            # Get action from DQN (20 normalized prices + position)
            state = np.concatenate(
                (self.normalisedPriceHistory, np.array([float(self.position)], dtype=np.float32)),
                axis=0,
            ).astype(np.float32)
            
            # Add previous transition to replay memory
            if self.lastAction is not None and self.lastState is not None:
                self.memory.add(self.lastState, self.lastAction, reward, state)
            
            # Select action using epsilon-greedy
            action = self._selectAction(state)
            self.lastState = state
            self.lastAction = action
            
            # Train on batch
            self._trainStep()
            
            # Periodically update target network
            self.steps += 1
            if self.steps % self.targetNetworkUpdateFrequency == 0:
                self._updateTargetNetwork()
                self._decayEpsilon()
            
            # Translate action to order
            if action == 0:
                # Do nothing
                return
            elif action == 1:
                # Buy 1 unit
                direction = OrderDirection.Buy
                volume = 1
            elif action == 2:
                # Buy 5 units
                direction = OrderDirection.Buy
                volume = 5
            elif action == 3:
                # Sell 1 unit
                direction = OrderDirection.Sell
                volume = 1
            elif action == 4:
                # Sell 5 units
                direction = OrderDirection.Sell
                volume = 5
            
            # Place market order
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))
            return
        
        if type == "EVENT_SIMULATION_STOP":
            print(f"{self.name()} simulation stopped")
            return
