from thesimulator import *

import numpy as np
import collections
import matplotlib.pyplot as plt

from dqn.agent import ManualDQLAgent


class DQLAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1))
        self.pTrade = float(params.get("pTrade", 1))
        
        # PnL manager agent
        self.pnlAgent = str(params.get("pnlAgent", "PNL"))
        
        # DQN hyperparameters
        alpha = float(params.get("alpha", 0.1))
        gamma = float(params.get("gamma", 0.99))
        batchSize = int(params.get("batchSize", 32))
        bufferCapacity = int(params.get("bufferCapacity", 60))
        self.target_update_freq = int(params.get("targetUpdateFreq", 10))
        
        # Book-keeping
        self.position = 0
        self.priceHistory = collections.deque(maxlen=20)
        self.normalized_price = 0.0
        self.price_trend = 0.0
        self.volatility = 0.0
        self.step_reward = 0.0
        self.oldPnl = 0.0
        self.target_position = None
        self._last_trade_price = None
        
        # Create environment and DQN agent
        self.dqn = ManualDQLAgent(
            state_size=4,
            action_size=3,
            learning_rate=alpha,
            gamma=gamma,
            batch_size=batchSize,
            buffer_capacity=bufferCapacity
        )

        self.training_steps = 0
        self._last_state = None
        self._last_action = None
        self.losses = []
    
    # State construction
    def _updateStateFeatures(self, newPrice):
        self.priceHistory.append(newPrice)
        
        # Normalized price (relative to first in window)
        base = self.priceHistory[0]
        self.normalized_price = np.log(newPrice / (base + 1e-8))
        self.normalized_price = np.clip(self.normalized_price, -1.0, 1.0)
        self.normalized_price = round(self.normalized_price, 1)
        
        # Price trend
        if len(self.priceHistory) >= 2:
            ret = (self.priceHistory[-1] - self.priceHistory[-2]) / (self.priceHistory[-2] + 1e-8)
            self.price_trend = 1.0 if ret > 0.0001 else (-1.0 if ret < -0.0001 else 0.0)
        
        # Volatility
        if len(self.priceHistory) >= 2:
            returns = np.diff(np.log(np.array(self.priceHistory)))
            self.volatility = float(np.std(returns)) if len(returns) > 0 else 0.0
            self.volatility = round(self.volatility, 1)
    
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
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())
            
            if lastTradePrice <= 0 or (bestAsk <= 0 and bestBid <= 0):
                return
            
            # Store market data for later use
            self._last_trade_price = lastTradePrice
            self._last_bestAsk = bestAsk
            self._last_bestBid = bestBid
            
            # Update state features
            self._updateStateFeatures(lastTradePrice)
            
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
            obs = np.array([
                float(self.position),
                self.normalized_price,
                self.price_trend,
                self.volatility
            ], dtype=np.float32)
            
            # Add previous transition to replay buffer
            if self._last_action is not None and self._last_state is not None:
                self.dqn.replay_buffer.add(
                    self._last_state,
                    self._last_action,
                    reward,
                    obs,
                    done=False
                )
            
            # Select action using epsilon-greedy
            action = self.dqn.select_action(obs, training=True)
            self._last_state = obs
            self._last_action = action
            
            # Train on batch
            loss = self.dqn.train_step()
            if loss is not None:
                self.losses.append(loss)
            
            # Periodically update target network
            self.training_steps += 1
            if self.training_steps % self.target_update_freq == 0:
                self.dqn.update_target_network()
                self.dqn.decay_epsilon()
            
            # Translate action to target position
            positions = [-1, 0, 1]
            target_position = positions[action]
            
            # Decide order direction and volume to move from current position to target
            positionChange = target_position - self.position
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
