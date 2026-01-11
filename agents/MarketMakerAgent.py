from thesimulator import *
import random
import math
import collections
import statistics

class MarketMakerAgent:

    def configure(self, params):
        # Generic parameters
        self.exchange = str(params["exchange"])
        self.interval = int(params["interval"])
        self.offset = int(params.get("offset", 1))
        self.trade_probability = float(params.get("trade_probability", 0.2))

        self.pnl_agent = str(params.get("pnlAgent", "PNL")) # PnL manager agent name

        # MarketMakerAgent-specific parameters
        self.starting_capital = float(params.get("starting_capital", 100000.0)) # starting capital (monetary units consistent with PnL manager outputs)
        self.omega = float(params.get("omega", 0.01)) # fraction of capital to risk (omega). Q_t = omega * K_t

        # Parameters for splitting liquidity and inventory control
        self.n_levels = int(params.get("levels", 3)) # number of distinct levels per side
        # maximum desired inventory (I_bar)
        self.I_bar = float(params.get("I_bar", 100.0))
        # adverse-selection strength (r)
        self.r = float(params.get("r", 0.5))
        # lookback for price change (l_k)
        self.l_k = int(params.get("l_k", 10))
        # price tick multiplier for placing orders across levels (fractional)
        self.tick = float(params.get("tick", 0.001))

        # Demand signal smoothing and price adjustment parameters (piece 3)
        # exponential smoothing weight for observed demand D_t
        self.alpha_demand = float(params.get("alpha_demand", 0.5))
        # threshold s beyond which demand moves mid-price
        self.demand_threshold = float(params.get("demand_threshold", 0.0))
        # small price fraction per unit of (D - s) to adjust mid-price
        self.demand_scale = float(params.get("demand_scale", 0.0001))
        # sensitivity of mid-price to inventory changes (c in the notes)
        self.c = float(params.get("c", 0.0))

        # Parameters for spread setting based on recent mid-price volatility
        # gamma scales sigma to a spread; xi is a minimum spread (price units)
        self.gamma_spread = float(params.get("gamma_spread", 1.0))
        self.xi = float(params.get("xi", 0.01))
        # tau controls spacing between levels: tick_distance = 10^-tau
        self.tau = float(params.get("tau", 2.0))

        # Price history for adverse-selection heuristic (used for sigma calculation)
        self.price_history = collections.deque(maxlen=self.l_k + 1)
        # Keep a separate mid-price history to compute volatility over previous 10 periods
        self.mid_history = collections.deque(maxlen=10)

        # Smoothed demand signal D~_t and accumulated demand in the current period
        self.D_tilde = 0.0
        self.current_period_demand = 0.0

        # Inventory tracking for I~ logic (keep two previous inventories to detect changes)
        self.prev_inventory_1 = 0
        self.prev_inventory_2 = 0
        self.I_tilde_prev = 0.0

        # Minimum liquidity unit and optional caps
        self.min_liquidity_unit = int(params.get("min_liquidity_unit", 1))
        self.max_total_liquidity = int(params.get("max_total_liquidity", 1000))

        # Internal pending state used while waiting for responses
        self._pending_liquidity = None  # tuple (buy_qty, sell_qty)  

    def receiveMessage(self, simulation, type, payload):
        currentTimestamp = simulation.currentTimestamp()

        if type == "EVENT_SIMULATION_START":
            # Schedule the first wakeup
            simulation.dispatchMessage(currentTimestamp, self.offset, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            # Subscribe to market orders so we can observe D_t (market order net demand)
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "SUBSCRIBE_EVENT_ORDER_MARKET", EmptyPayload())

            return

        if type == "WAKE_UP":
            # Schedule the next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())

            # Before requesting PnL, update the smoothed market demand D~ using the accumulated market orders
            D_t = self.current_period_demand
            # update smoothed demand (exponential smoothing); if first period, this will simply set D_tilde to D_t
            self.D_tilde = self.alpha_demand * D_t + (1.0 - self.alpha_demand) * self.D_tilde
            # reset period demand accumulator
            self.current_period_demand = 0.0

            # Request a PnL snapshot from the PnL manager to compute available capital
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnl_agent, "REQUEST_PNL", EmptyPayload())
            return

        if type == "EVENT_ORDER_MARKET":
            # Observe market orders arriving during the period and accumulate signed net demand D_t
            # payload.order.direction: OrderDirection.Buy/Sell
            # payload.order.volume: Volume
            try:
                mo = payload.order
                vol = int(getattr(mo, 'volume', 0))
                dir = getattr(mo, 'direction', None)
                if dir == OrderDirection.Buy:
                    self.current_period_demand += vol
                else:
                    self.current_period_demand -= vol
            except Exception:
                # If payload structure differs, ignore
                pass
            return

        if type == "RESPONSE_PNL":

            # Received PnL response from PnLManagerAgent
            realized = float(payload.realized_pnl.toCentString())
            unrealized = float(payload.unrealized_pnl.toCentString())
            inventory = int(getattr(payload, "inventory", 0))

            # shift inventory history and store latest inventory for quoting logic
            self.prev_inventory_2 = self.prev_inventory_1
            self.prev_inventory_1 = inventory
            self.inventory = inventory

            # Available capital = starting capital + realized + mark-to-market (unrealized)
            capital = self.starting_capital + realized + unrealized

            # Total liquidity to offer (floor to integer units)
            total_liquidity = int(math.floor(self.omega * capital))

            # Enforce bounds
            if total_liquidity < self.min_liquidity_unit:
                # Not enough capital to provide liquidity this period
                self._pending_liquidity = None
                return
            if total_liquidity > self.max_total_liquidity:
                total_liquidity = self.max_total_liquidity

            # Split roughly equally between buy and sell
            buy_qty = total_liquidity // 2
            sell_qty = total_liquidity - buy_qty

            # Save pending quantities and request L1 data to choose prices
            self._pending_liquidity = (buy_qty, sell_qty)
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", RetrieveL1Payload())
            return

        if type == "RESPONSE_RETRIEVE_L1":
            if self._pending_liquidity is None:
                return

            buy_qty, sell_qty = self._pending_liquidity
            self._pending_liquidity = None

            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            # Update price history for adverse-selection calculation
            if lastTradePrice > 0:
                self.price_history.append(lastTradePrice)

            # Adverse-selection factor: scale down supply when recent price moves are large
            selection_factor = 1.0
            if len(self.price_history) >= (self.l_k + 1):
                p_now = self.price_history[-1]
                p_past = self.price_history[-1 - self.l_k]
                if p_past > 0:
                    price_change = abs(p_now - p_past) / p_past
                    selection_factor = max(0.0, 1.0 - self.r * price_change)

            # Inventory adjustment: reduce bids when long, reduce asks when short
            inventory = getattr(self, 'inventory', 0)
            inv_ratio = inventory / float(self.I_bar) if self.I_bar != 0 else 0.0
            bid_factor = max(0.0, 1.0 - inv_ratio)
            ask_factor = max(0.0, 1.0 + inv_ratio)

            # === New: mid-price adjustment using demand signal D~ and inventory I~ ===
            # Determine previous market mid-price
            prev_mid = None
            if bestAsk > 0 and bestBid > 0:
                prev_mid = 0.5 * (bestAsk + bestBid)
            elif lastTradePrice > 0:
                prev_mid = lastTradePrice

            # Demand-based adjustment
            demand_adj = 0.0
            if abs(self.D_tilde) > self.demand_threshold:
                if self.D_tilde > self.demand_threshold:
                    demand_adj = self.demand_scale * (self.D_tilde - self.demand_threshold)
                elif self.D_tilde < -self.demand_threshold:
                    demand_adj = self.demand_scale * (self.D_tilde + self.demand_threshold)

            # Inventory tilde: update only if inventory changed in the last period
            I_tilde = self.I_tilde_prev
            if abs(self.prev_inventory_1 - self.prev_inventory_2) > 0:
                # c * (I_k,t / I_bar)
                I_tilde = self.c * (inventory / float(self.I_bar)) if self.I_bar != 0 else 0.0

            # Inventory-based price adjustment: down if long, up if short
            inv_adj = 0.0
            if prev_mid is not None:
                inv_adj = - prev_mid * I_tilde

            # store I_tilde for next period
            self.I_tilde_prev = I_tilde

            # Target mid-price
            mid_target = prev_mid if prev_mid is not None else None
            if mid_target is not None:
                mid_target = mid_target + demand_adj + inv_adj

            # === New: set spread width based on historical mid-price volatility ===
            # Compute volatility sigma over previous up-to-10 mid prices (t-1 : t-10)
            sigma = 0.0
            if len(self.mid_history) >= 2:
                sample = list(self.mid_history)
                # use population std dev as a proxy
                try:
                    sigma = statistics.pstdev(sample)
                except Exception:
                    sigma = 0.0

            # spread component is at least xi and otherwise gamma_spread * sigma
            spread_component = max(self.gamma_spread * sigma, self.xi)
            # tick spacing between subsequent levels
            tick_distance = 10.0 ** (-self.tau)

            # record current prev_mid into mid_history for future volatility calc
            if prev_mid is not None:
                try:
                    self.mid_history.append(prev_mid)
                except Exception:
                    pass

            # Determine levels and per-level base quantities
            levels = max(1, int(self.n_levels))
            base_buy = float(buy_qty) / levels
            base_sell = float(sell_qty) / levels

            # Place multiple limit orders across levels on each side using mid_target
            for i in range(levels):
                # Bid side
                q_bid = int(math.floor(base_buy * bid_factor * selection_factor))
                if q_bid >= self.min_liquidity_unit:
                    bid_price = None
                    if mid_target is not None:
                        # place bids at mid minus spread and level spacing
                        bid_price = mid_target - spread_component - (i + 1) * tick_distance
                    elif bestBid > 0:
                        bid_price = bestBid * (1.0 - i * self.tick)
                    elif lastTradePrice > 0:
                        bid_price = lastTradePrice * (1.0 - (i + 1) * self.tick)

                    if bid_price is not None and q_bid > 0:
                        simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Buy, q_bid, Money(bid_price)))

                # Ask side
                q_ask = int(math.floor(base_sell * ask_factor * selection_factor))
                if q_ask >= self.min_liquidity_unit:
                    ask_price = None
                    if mid_target is not None:
                        # place asks at mid plus spread and level spacing
                        ask_price = mid_target + spread_component + (i + 1) * tick_distance
                    elif bestAsk > 0:
                        ask_price = bestAsk * (1.0 + i * self.tick)
                    elif lastTradePrice > 0:
                        ask_price = lastTradePrice * (1.0 + (i + 1) * self.tick)

                    if ask_price is not None and q_ask > 0:
                        simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "PLACE_ORDER_LIMIT", PlaceOrderLimitPayload(OrderDirection.Sell, q_ask, Money(ask_price)))

            return
