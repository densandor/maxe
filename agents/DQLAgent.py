from thesimulator import *
from dqn.Network import Network
from dqn.ReplayMemory import ReplayMemory

import numpy as np
import collections
import matplotlib.pyplot as plt
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
        self.alpha = float(params.get("alpha", 0.1))
        self.gamma = float(params.get("gamma", 0.99))
        self.epsilon = float(params.get("epsilon", 1.0))
        self.minEpsilon = float(params.get("minEpsilon", 0.01))
        self.epsilonDecay = float(params.get("epsilonDecay", 0.995))
        self.batchSize = int(params.get("batchSize", 6))
        self.memoryCapacity = int(params.get("memoryCapacity", 60))
        self.targetNetworkUpdateFrequency = int(params.get("targetNetworkUpdateFrequency", 10))
        
        # State features
        self.position = 0 # Feature 1: Current position (-1, 0, 1)
        self.priceHistory = collections.deque(maxlen=20)
        self.normalisedPrice = 0.0 # Feature 2: Normalised price
        self.priceTrend = 0.0 # Feature 3: Price trend
        self.volatility = 0.0 # Feature 4: Volatility
        self.oldPnl = 0.0

        self.actionSpaceSize = 3 # Actions: Sell, Hold, Buy
        
        # Initialise networks
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.qNetwork = Network(4, 3).to(self.device)
        self.targetNetwork = Network(4, 3).to(self.device)
        self.steps = 0
        self.lastState = None
        self.lastAction = None
        # Initialise target with same weights as Q-network
        self.targetNetwork.load_state_dict(self.qNetwork.state_dict())
        self.targetNetwork.eval() # Target network never trains
        
        # Initialise optimiser and loss
        self.optimiser = optim.Adam(self.qNetwork.parameters(), lr=self.alpha)
        self.lossFunction = nn.MSELoss()
        self.losses = []
        
        # Initialise replay buffer
        self.memory = ReplayMemory(capacity=self.memoryCapacity)   

    def _updateState(self, newPrice):
        self.priceHistory.append(newPrice)
        
        # Normalized price (relative to first in window)
        base = self.priceHistory[0]
        self.normalisedPrice = np.log(newPrice / (base + 1e-8))
        self.normalisedPrice = np.clip(self.normalisedPrice, -1.0, 1.0)
        self.normalisedPrice = round(self.normalisedPrice, 1)
        
        # Price trend
        if len(self.priceHistory) >= 2:
            ret = (self.priceHistory[-1] - self.priceHistory[-2]) / (self.priceHistory[-2] + 1e-8)
            self.priceTrend = 1.0 if ret > 0.0001 else (-1.0 if ret < -0.0001 else 0.0)
        
        # Volatility
        if len(self.priceHistory) >= 2:
            returns = np.diff(np.log(np.array(self.priceHistory)))
            self.volatility = float(np.std(returns)) if len(returns) > 0 else 0.0
            self.volatility = round(self.volatility, 1)

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
            
            # Get action from DQN
            state = np.array([float(self.position), self.normalisedPrice, self.priceTrend,self.volatility], dtype=np.float32)
            
            # Add previous transition to replay memory
            if self.lastAction is not None and self.lastState is not None:
                self.memory.add(self.lastState, self.lastAction, reward, state)
            
            # Select action using epsilon-greedy
            action = self._selectAction(state)
            self.lastState = state
            self.lastAction = action
            
            # Train on batch
            loss = self._trainStep()
            if loss is not None:
                self.losses.append(loss)
            
            # Periodically update target network
            self.steps += 1
            if self.steps % self.targetNetworkUpdateFrequency == 0:
                self._updateTargetNetwork()
                self._decayEpsilon()
            
            # Translate action to target position
            positions = [-1, 0, 1]
            targetPosition = positions[action]
            
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
        
        if type == "EVENT_SIMULATION_STOP":
            print(f"{self.name()} simulation stopped")
            plt.plot(self.losses)
            plt.title("DQL Agent Training Loss")
            plt.xlabel("Training Steps")
            plt.ylabel("Loss")
            plt.show()
            return
