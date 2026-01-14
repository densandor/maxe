from thesimulator import *
import numpy as np
from stable_baselines3 import DQN
from gymnasium import Env, spaces


class TradingEnv(Env):
    """Minimal trading environment wrapper for Stable-Baselines3."""
    
    def __init__(self, agent):
        super(TradingEnv, self).__init__()
        self.agent = agent
        
        # State: [position, normalized_last_price, price_trend, volatility]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(4,), dtype=np.float32
        )
        
        # Action space: 40 discrete actions
        # 0-39: side(2) × order_type(2) × price(5) × volume(2)
        self.action_space = spaces.Discrete(40)
        
        # Price/volume choices (relative to first price in series)
        self.price_offsets = [-0.02, -0.01, 0.0, 0.01, 0.02]  # ±2%, ±1%, mid
        self.volumes = [1, 2]
        
        # Tracking
        self.last_reward = 0.0
        self.done = False
    
    def reset(self, seed=None):
        """Reset at episode start."""
        super().reset(seed=seed)
        state = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        return state, {}
    
    def step(self, action):
        """Convert action int to (side, order_type, price, volume) and return reward."""
        # Decode action: 40 = 2*2*5*2
        side = action // 20  # 0 (sell) or 1 (buy)
        order_type = (action % 20) // 10  # 0 (limit) or 1 (market)
        price_idx = (action % 10) // 2  # 0-4 (5 price levels)
        volume_idx = action % 2  # 0 or 1 (2 volumes)
        
        # Store decoded action in agent for use in receiveMessage()
        self.agent.decoded_action = {
            'side': side,
            'order_type': order_type,
            'price_offset': self.price_offsets[price_idx],
            'volume': self.volumes[volume_idx]
        }
        
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
        self.interval = int(params["interval"])
        self.offset = int(params.get("offset", 1))
        
        # DQN hyperparameters (passed to Stable-Baselines3)
        learning_rate = float(params.get("learning_rate", 1e-4))
        gamma = float(params.get("gamma", 0.99))
        exploration_fraction = float(params.get("exploration_fraction", 0.1))
        exploration_final_eps = float(params.get("exploration_final_eps", 0.01))
        batch_size = int(params.get("batch_size", 32))
        pretrained_weights = str(params.get("pretrained_weights", ""))
        
        # Book-keeping
        self.pnl = PnLTracker()
        self.position = 0
        self.price_history = []
        self.normalized_price = 0.0
        self.price_trend = 0.0
        self.volatility = 0.0
        self.step_reward = 0.0
        self.last_pnl = 0.0
        self.first_price = None
        self.decoded_action = None
        
        # Create environment and DQN agent
        self.env = TradingEnv(self)
        
        if pretrained_weights:
            try:
                self.dqn = DQN.load(pretrained_weights, env=self.env)
                print(f"{self.name()} loaded pretrained model from {pretrained_weights}")
            except Exception as e:
                print(f"{self.name()} failed to load: {e}")
                self.dqn = DQN(
                    "MlpPolicy",
                    self.env,
                    learning_rate=learning_rate,
                    gamma=gamma,
                    exploration_fraction=exploration_fraction,
                    exploration_final_eps=exploration_final_eps,
                    batch_size=batch_size,
                    verbose=0
                )
        else:
            self.dqn = DQN(
                "MlpPolicy",
                self.env,
                learning_rate=learning_rate,
                gamma=gamma,
                exploration_fraction=exploration_fraction,
                exploration_final_eps=exploration_final_eps,
                batch_size=batch_size,
                verbose=0
            )
    
    # --- State construction ---
    
    def _update_state_features(self, new_price):
        """Update price history and compute trend/volatility."""
        self.price_history.append(new_price)
        if len(self.price_history) > 20:
            self.price_history.pop(0)
        
        # Set first price for normalization
        if self.first_price is None:
            self.first_price = new_price
        
        # Normalized price (relative to first in window)
        base = self.price_history[0] if self.price_history else self.first_price
        self.normalized_price = np.log(new_price / (base + 1e-8))
        self.normalized_price = np.clip(self.normalized_price, -1.0, 1.0)
        
        # Price trend
        if len(self.price_history) >= 2:
            ret = (self.price_history[-1] - self.price_history[-2]) / (self.price_history[-2] + 1e-8)
            self.price_trend = 1.0 if ret > 0.0001 else (-1.0 if ret < -0.0001 else 0.0)
        
        # Volatility
        if len(self.price_history) >= 2:
            returns = np.diff(np.log(np.array(self.price_history)))
            self.volatility = float(np.std(returns)) if len(returns) > 0 else 0.0
    
    # --- Messaging ---
    
    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()
        
        if type == "EVENT_SIMULATION_START":
            simulation.dispatchMessage(
                currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload()
            )
            return
        
        if type == "WAKE_UP":
            simulation.dispatchMessage(
                currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload()
            )
            simulation.dispatchMessage(
                currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", RetrieveL1Payload()
            )
            return
        
        if type == "RESPONSE_RETRIEVE_L1":
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())
            
            if lastTradePrice <= 0 or (bestAsk <= 0 and bestBid <= 0):
                return
            
            # Update PnL and state
            self.pnl.mark_to_market(lastTradePrice)
            self._update_state_features(lastTradePrice)
            
            # Compute reward
            current_pnl = self.pnl.snapshot()
            reward = current_pnl - self.last_pnl
            self.last_pnl = current_pnl
            self.step_reward = reward
            
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
            
            # Decode action
            if self.decoded_action is None:
                return
            
            side = self.decoded_action['side']  # 0=sell, 1=buy
            order_type = self.decoded_action['order_type']  # 0=limit, 1=market
            price_offset = self.decoded_action['price_offset']
            volume = self.decoded_action['volume']
            
            # Compute limit price (relative to first price in window)
            base_price = self.price_history[0] if self.price_history else lastTradePrice
            limit_price = base_price * (1.0 + price_offset)
            
            # Decide whether to actually trade
            if order_type == 1:  # market order
                direction = OrderDirection.Buy if side == 1 else OrderDirection.Sell
                simulation.dispatchMessage(
                    currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET",
                    PlaceOrderMarketPayload(direction, volume)
                )
            else:  # limit order
                direction = OrderDirection.Buy if side == 1 else OrderDirection.Sell
                simulation.dispatchMessage(
                    currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT",
                    PlaceOrderLimitPayload(direction, volume, int(limit_price * 100))  # convert to cents
                )
            
            return
        
        if type == "RESPONSE_PLACE_ORDER_MARKET" or type == "RESPONSE_PLACE_ORDER_LIMIT":
            order_id = payload.id
            sub_payload = SubscribeEventTradeByOrderPayload(order_id)
            simulation.dispatchMessage(
                currentTimestamp, 0, self.name(), self.exchange, "SUBSCRIBE_EVENT_ORDER_TRADE", sub_payload
            )
            return
        
        if type == "EVENT_TRADE":
            trade = payload.trade
            fill_price = float(trade.price().toCentString())
            fill_volume = int(trade.volume())
            direction = trade.direction()
            
            self.pnl.update_pnl_on_fill(fill_price, fill_volume, direction)
            if direction == OrderDirection.Buy:
                self.position += fill_volume
            elif direction == OrderDirection.Sell:
                self.position -= fill_volume
            self.position = max(-1, min(1, self.position))
            return
        
        if type == "EVENT_SIMULATION_STOP":
            print(self.name(), self.pnl.snapshot())
            # Save trained model
            try:
                self.dqn.save(f"{self.name()}_model")
                print(f"{self.name()} saved model to {self.name()}_model.zip")
            except Exception as e:
                print(f"{self.name()} failed to save: {e}")
            return
