from thesimulator import *
from PnLTracker import PnLTracker
import random
import numpy as np


class QLearningAgent:
    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.interval = int(params["interval"])
        self.offset = int(params.get("offset", 1))

        # Q-learning parameters
        self.alpha = float(params.get("alpha", 0.1)) # learning rate
        self.gamma = float(params.get("gamma", 0.99)) # discount factor
        self.epsilon = float(params.get("epsilon", 0.1)) # exploration rate
        self.epsilon_min = float(params.get("epsilon_min", 0.01))
        self.epsilon_decay = float(params.get("epsilon_decay", 0.999))

        # Discrete state design: position ∈ {-1, 0, +1}, price trend ∈ {-1, 0, +1}
        # Encode state index as (position_idx * 3 + trend_idx) in [0, 8]
        self.positions = [-1, 0, 1]
        self.trends = [-1, 0, 1]

        # Action space: 0 = go short 1, 1 = go flat, 2 = go long 1
        self.action_space = [0, 1, 2]

        # Q-table: 9 states x 3 actions
        self.Q = np.zeros((len(self.positions) * len(self.trends), len(self.action_space)))

        # Book-keeping
        self.pnl = PnLTracker()
        self.position = 0           # current signed position (−1, 0, +1)
        self.last_price = None      # last trade price seen
        self.prev_state = None
        self.prev_action = None

    # --- Helper methods for state / action encoding ---

    def _discretize_trend(self, last_price, new_price, threshold=0.0001):
        """Very simple trend: up, down, or flat based on relative price change."""
        if last_price is None or last_price <= 0:
            return 0
        ret = (new_price - last_price) / last_price
        if ret > threshold:
            return 1
        elif ret < -threshold:
            return -1
        else:
            return 0

    def _state_to_index(self, position, trend):
        pos_idx = self.positions.index(position)
        tr_idx = self.trends.index(trend)
        return pos_idx * len(self.trends) + tr_idx

    def _epsilon_greedy(self, state_idx):
        if random.random() < self.epsilon:
            return random.choice(self.action_space)
        else:
            return int(np.argmax(self.Q[state_idx, :]))

    # --- Q-learning update ---

    def _update_q(self, reward, new_state_idx):
        if self.prev_state is None or self.prev_action is None:
            return
        s = self.prev_state
        a = self.prev_action
        best_next = np.max(self.Q[new_state_idx, :])
        td_target = reward + self.gamma * best_next
        td_error = td_target - self.Q[s, a]
        self.Q[s, a] += self.alpha * td_error

    # --- Messaging ---

    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            # Schedule first wake-up
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            return

        if type == "WAKE_UP":
            # Schedule next wakeup
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            # Request L1 data from the exchange
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", RetrieveL1Payload())
            return

        if type == "RESPONSE_RETRIEVE_L1":
            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            if lastTradePrice <= 0 or (bestAsk <= 0 and bestBid <= 0):
                return

            # Update mark-to-market PnL
            self.pnl.mark_to_market(lastTradePrice)

            # Compute simple trend
            trend = self._discretize_trend(self.last_price, lastTradePrice)
            self.last_price = lastTradePrice

            # Current state index
            state_idx = self._state_to_index(self.position, trend)

            # Reward: change in total PnL since last step
            current_pnl = self.pnl.snapshot()["total_pnl"]
            if not hasattr(self, "last_pnl"):
                self.last_pnl = current_pnl
            reward = current_pnl - self.last_pnl
            self.last_pnl = current_pnl

            # Q-learning update from previous transition
            if self.prev_state is not None and self.prev_action is not None:
                self._update_q(reward, state_idx)

            # Choose new action
            action = self._epsilon_greedy(state_idx)

            # Decay epsilon (optional)
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay

            # Translate action to target position
            target_position = -1 if action == 0 else (0 if action == 1 else 1)

            # Decide order direction and volume to move from current position to target
            delta_pos = target_position - self.position
            if delta_pos == 0:
                # No trade
                self.prev_state = state_idx
                self.prev_action = action
                return

            direction = OrderDirection.Buy if delta_pos > 0 else OrderDirection.Sell
            volume = abs(delta_pos)  # single-unit steps

            if volume <= 0:
                self.prev_state = state_idx
                self.prev_action = action
                return

            # Place market order to change position
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_MARKET", PlaceOrderMarketPayload(direction, volume))

            # Store previous state/action for next update
            self.prev_state = state_idx
            self.prev_action = action
            return

        if type == "RESPONSE_PLACE_ORDER_MARKET":
            order_id = payload.id
            sub_payload = SubscribeEventTradeByOrderPayload(order_id)
            simulation.dispatchMessage(
                currentTimestamp,
                0,
                self.name(),
                self.exchange,
                "SUBSCRIBE_EVENT_ORDER_TRADE",
                sub_payload
            )
            return

        if type == "EVENT_TRADE":
            trade = payload.trade
            fill_price = float(trade.price().toCentString())
            fill_volume = int(trade.volume())
            direction = trade.direction()
            print(fill_price, fill_volume, direction)

            # Update PnL and position on fill
            self.pnl.update_pnl_on_fill(fill_price, fill_volume, direction)
            if direction == OrderDirection.Buy:
                self.position += fill_volume
            elif direction == OrderDirection.Sell:
                self.position -= fill_volume
            return

        if type == "EVENT_SIMULATION_STOP":
            print(self.name(), self.pnl.snapshot())
            return
