from thesimulator import *
import numpy as np
import collections
from stable_baselines3 import DQN
from gymnasium import Env, spaces

class TradingEnv(Env):
    """Minimal trading environment wrapper for Stable-Baselines3."""
    
    def __init__(self, agent):
        super(TradingEnv, self).__init__()
        self.agent = agent
        
        # State: [position, normalized_last_price, price_trend, volatility]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(4,), dtype=np.float32)
        
        # Action space: 3 discrete actions
        # 0: go short 1, 1: go flat, 2: go long 1
        self.action_space = spaces.Discrete(3)
        
        # Tracking
        self.last_reward = 0.0
        self.done = False
    
    def reset(self, seed=None):
        """Reset at episode start."""
        super().reset(seed=seed)
        state = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        return state, {}
    
    def step(self, action):
        """Convert action int to target position and return reward."""
        # Decode action: 0 = go short 1, 1 = go flat, 2 = go long 1
        positions = [-1, 0, 1]
        target_position = positions[action]
        
        # Store target position in agent for use in receiveMessage()
        self.agent.target_position = target_position
        
        # Reward is PnL change (set by agent in receiveMessage)
        reward = self.agent.step_reward
        
        # Obs: [position, normalized_price, trend, volatility]
        obs = np.array([
            float(self.agent.position),
            self.agent.normalized_price,
            self.agent.price_trend,
            self.agent.volatility
        ], dtype=np.float32)
        
        return obs, reward, self.done, False, {}


class DQLAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.offset = int(params.get("offset", 1))
        self.interval = int(params.get("interval", 1000))
        self.pTrade = float(params.get("pTrade", 1))
        
        # PnL manager agent
        self.pnlAgent = str(params.get("pnlAgent", "PNL"))
        
        # DQN hyperparameters
        alpha = float(params.get("alpha", 0.1))
        gamma = float(params.get("gamma", 0.99))
        explorationFraction = float(params.get("explorationFraction", 0.1))
        explorationFinalEps = float(params.get("explorationFinalEps", 0.01))
        batchSize = int(params.get("batchSize", 32))
        pretrainedWeights = str(params.get("pretrainedWeights", ""))
        
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
        self.env = TradingEnv(self)
        
        if pretrainedWeights:
            try:
                self.dqn = DQN.load(pretrainedWeights, env=self.env)
                print(f"{self.name()} loaded pretrained model from {pretrainedWeights}")
            except Exception as e:
                print(f"{self.name()} failed to load: {e}")
                self.dqn = DQN(
                    "MlpPolicy",
                    self.env,
                    learning_rate=alpha,
                    gamma=gamma,
                    exploration_fraction=explorationFraction,
                    exploration_final_eps=explorationFinalEps,
                    batch_size=batchSize,
                    learning_starts=0,
                    buffer_size=60,
                    verbose=1
                )
        else:
            self.dqn = DQN(
                "MlpPolicy",
                self.env,
                learning_rate=alpha,
                gamma=gamma,
                exploration_fraction=explorationFraction,
                exploration_final_eps=explorationFinalEps,
                batch_size=batchSize,
                learning_starts=0,
                buffer_size=60,
                verbose=1
            )
    
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
            self.step_reward = totalPnl - self.oldPnl
            self.oldPnl = totalPnl
            
            # Get action from DQN
            obs = np.array([
                float(self.position),
                self.normalized_price,
                self.price_trend,
                self.volatility
            ], dtype=np.float32)
            
            action, _ = self.dqn.predict(obs, deterministic=False)
            
            # Train DQN (online learning)
            self.dqn.learn(total_timesteps=1)
            
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
            try:
                self.dqn.save(f"{self.name()}_model")
                print(f"{self.name()} saved model to {self.name()}_model.zip")
            except Exception as e:
                print(f"{self.name()} failed to save: {e}")
            return
