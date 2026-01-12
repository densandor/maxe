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
        self.trade_probability = float(params.get("tradeProbability", 0.2))

        self.pnl_agent = str(params.get("pnlAgent", "PNL")) # PnL manager agent name
        self.market_data_agent = str(params.get("marketDataAgent", "MARKET_DATA")) # Market data agent name

        # MarketMakerAgent-specific parameters
        self.starting_capital = float(params.get("startingCapital", 100000.0)) # starting capital
        self.capital_risk_multiplier = float(params.get("capitalRiskMultiplier", 0.2)) # fraction of capital to risk

        # Parameters for splitting liquidity and managing inventory
        self.orders_each_side = int(params.get("ordersEachSide", 4)) # number of distinct price levels per side
        self.max_inventory = float(params.get("maxInventory", 100.0))
        self.adverse_selection_multiplier = float(params.get("r", 1000)) # sensitivity to price changes for adverse selection
        self.lookback = int(params.get("lookback", 10)) # lookback for price change (lookback)
        self.tick = float(params.get("tick", 0.001)) # price tick multiplier for placing orders across levels (fractional)

        # Demand signal smoothing and price adjustment parameters
        self.demand_smoothing = float(params.get("demandSmoothing", 0.15)) # exponential smoothing weight for observed demand (D)
        self.demand_threshold = float(params.get("demandThreshold", 0.0)) # threshold beyond which demand moves mid-price (s)
        self.demand_scale = float(params.get("demandScale", 0.0001)) # small price fraction per unit of (D - s) to adjust mid-price
        self.c = float(params.get("c", 0.0)) # sensitivity of mid-price to inventory changes

        # Parameters for spread setting based on recent mid-price volatility
        # gamma scales sigma to a spread; xi is a minimum spread (price units)
        self.gamma_spread = float(params.get("gamma_spread", 1.0))
        self.xi = float(params.get("xi", 0.01))
        # tau controls spacing between levels: tick_distance = 10^-tau
        self.tau = float(params.get("tau", 2.0))

        # Price history for adverse-selection heuristic (used for sigma calculation)
        self.price_history = collections.deque(maxlen=self.lookback + 1)
        # Keep a separate mid-price history to compute volatility over previous 10 periods
        self.mid_history = collections.deque(maxlen=10)

        self.demand_signal = 0.0 # smoothed demand D~
        self.current_demand = 0.0 # demand at current wake-up

        # Inventory tracking for I~ logic (keep two previous inventories to detect changes)
        self.inventory_t_minus_1 = 0
        self.inventory_t_minus_2 = 0
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
            return

        if type == "WAKE_UP":
            # Schedule the next wakeup
            simulation.dispatchMessage(currentTimestamp, self.interval, self.name(), self.name(), "WAKE_UP", EmptyPayload())
            # Request market data to update demand signal and plan liquidity provision
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.market_data_agent, "REQUEST_MARKET_DATA", EmptyPayload())
            return
        
        if type == "RESPONSE_REQUEST_MARKET_DATA":
            # Before requesting PnL, update the smoothed market demand using the accumulated market orders
            current_demand = payload.demand # signed integer: buys positive, sells negative
            # update smoothed demand (exponential smoothing); if first period, this will simply set demand_signal to current_demand
            self.demand_signal = self.demand_smoothing * current_demand + (1.0 - self.demand_smoothing) * self.demand_signal

            # Request a PnL snapshot from the PnL manager to compute available capital
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.pnl_agent, "REQUEST_PNL", EmptyPayload())
            return
        
        if type == "RESPONSE_PNL":
            # Received PnL response from PnLManagerAgent
            realized = float(payload.realized_pnl)
            unrealized = float(payload.unrealized_pnl)
            inventory = int(getattr(payload, "inventory", 0))

            # shift inventory history and store latest inventory for quoting logic
            self.prev_inventory_2 = self.prev_inventory_1
            self.prev_inventory_1 = self.inventory
            self.inventory = inventory

            # Available capital = starting capital + realized + mark-to-market (unrealized)
            capital = self.starting_capital + realized + unrealized

            # Total liquidity to offer (floor to integer units)
            total_liquidity = int(math.floor(self.capital_risk_multiplier * capital))

            # Enforce bounds
            if total_liquidity < self.min_liquidity_unit:
                # Not enough capital to provide liquidity this period
                self._pending_liquidity = None
                return
            if total_liquidity > self.max_total_liquidity:
                total_liquidity = self.max_total_liquidity

            # Split roughly equally between buy and sell
            one_side_liquidity = total_liquidity // 2

            # Save pending quantities and request L1 data to choose prices
            self._pending_liquidity = one_side_liquidity
            simulation.dispatchMessage(currentTimestamp, 0, self.name(), self.exchange, "RETRIEVE_L1", EmptyPayload())
            return

        if type == "RESPONSE_RETRIEVE_L1":
            if self._pending_liquidity is None:
                return

            one_side_liquidity = self._pending_liquidity
            self._pending_liquidity = None

            bestAsk = float(payload.bestAskPrice.toCentString())
            bestBid = float(payload.bestBidPrice.toCentString())
            lastTradePrice = float(payload.lastTradePrice.toCentString())

            # Update price history for adverse-selection calculation
            if lastTradePrice > 0:
                self.price_history.append(lastTradePrice)

            # Adverse-selection factor: scale down supply when recent price moves are large
            selection_factor = 1.0
            if len(self.price_history) >= (self.lookback + 1):
                p_now = self.price_history[-1]
                p_past = self.price_history[-1 - self.lookback]
                if p_past > 0:
                    price_change = abs(p_now - p_past) / p_past
                    selection_factor = max(0.0, 1.0 - self.adverse_selection_multiplier * price_change)

            # Inventory adjustment: reduce bids when long, reduce asks when short
            inventory = getattr(self, 'inventory', 0)
            inv_ratio = inventory / float(self.max_inventory) if self.max_inventory != 0 else 0.0
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
            if abs(self.demand_signal) > self.demand_threshold:
                if self.demand_signal > self.demand_threshold:
                    demand_adj = self.demand_scale * (self.demand_signal - self.demand_threshold)
                elif self.demand_signal < -self.demand_threshold:
                    demand_adj = self.demand_scale * (self.demand_signal + self.demand_threshold)

            # Inventory tilde: update only if inventory changed in the last period
            I_tilde = self.I_tilde_prev
            if abs(self.prev_inventory_1 - self.prev_inventory_2) > 0:
                # c * (I_k,t / max_inventory)
                I_tilde = self.c * (inventory / float(self.max_inventory)) if self.max_inventory != 0 else 0.0

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
            levels = max(1, int(self.orders_each_side))
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
