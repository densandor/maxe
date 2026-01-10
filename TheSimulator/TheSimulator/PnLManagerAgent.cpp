#include "PnLManagerAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>
#include <iomanip>

PnLManagerAgent::PnLManagerAgent(const Simulation* simulation)
	: Agent(simulation), m_exchange(""), m_last_trade_price(Money(0)) { }

PnLManagerAgent::PnLManagerAgent(const Simulation* simulation, const std::string& name)
	: Agent(simulation, name), m_exchange(""), m_last_trade_price(Money(0)) { }

void PnLManagerAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
	Agent::configure(node, configurationPath);

	pugi::xml_attribute att;
	if (!(att = node.attribute("exchange")).empty()) {
		m_exchange = simulation()->parameters().processString(att.as_string());
	}
}

void PnLManagerAgent::receiveMessage(const MessagePtr& msg) {
	const Timestamp currentTimestamp = simulation()->currentTimestamp();
	
	if (msg->type == "EVENT_SIMULATION_START") {
		// subscribe to trades on configured exchange
		simulation()->dispatchMessage(currentTimestamp, currentTimestamp, name(), m_exchange, "SUBSCRIBE_EVENT_TRADE", std::make_shared<EmptyPayload>());
	} else if (msg->type == "EVENT_TRADE") {
		auto pptr = std::dynamic_pointer_cast<EventTradePayload>(msg->payload);
		const auto& trade = pptr->trade;

		// update last trade price
		m_last_trade_price = trade.price();

		// aggressor side
		updateOnFill(trade.aggressingOwner(), trade.price(), trade.volume(), trade.direction());

		// resting side -> opposite direction
		OrderDirection restingDir = (trade.direction() == OrderDirection::Buy ? OrderDirection::Sell : OrderDirection::Buy);
		updateOnFill(trade.restingOwner(), trade.price(), trade.volume(), restingDir);

	} else if (msg->type == "REQUEST_PNL") {
		// Respond to a PnL snapshot request for msg->source
		const std::string requester = msg->source;

		int inventory = 0;
		Money avg_price = Money(0);
		Money realized = Money(0);
		Money unrealized = Money(0);
		Money lastPrice = m_last_trade_price;

		auto it = m_states.find(requester);
		if (it != m_states.end()) {
			const PnLState& s = it->second;
			inventory = s.inventory;
			avg_price = s.avg_price;
			realized = s.realized_pnl;
			if (s.inventory != 0 && lastPrice != Money(0) && s.avg_price != Money(0)) {
				unrealized = (lastPrice - s.avg_price) * s.inventory;
			}
		}

		auto resp = std::make_shared<ResponsePnLPayload>(inventory, avg_price, realized, unrealized, lastPrice);
		simulation()->dispatchMessage(currentTimestamp, 0, name(), requester, "RESPONSE_PNL", resp);

	} else if (msg->type == "EVENT_SIMULATION_STOP") {
		// Snapshot and print final per-agent stats (lazy MTM)
		std::cout << "\n=== Final PnL summary (agent, inventory, avg_price, realized_pnl, unrealized_pnl, last_price) ===\n";
		for (const auto& kv : m_states) {
			const std::string& agent = kv.first;
			const PnLState& s = kv.second;

			Money unrealized = Money(0);
			Money lastPrice = m_last_trade_price;
			if (s.inventory != 0 && lastPrice != Money(0) && s.avg_price != Money(0)) {
				unrealized = (lastPrice - s.avg_price) * s.inventory;
			}

			// Print deterministic columns using Money::toCentString()
			std::cout << agent << ", "
				<< s.inventory << ", " << s.avg_price.toCentString() << ", "
				<< s.realized_pnl.toCentString() << ", " << unrealized.toCentString() << ", " << lastPrice.toCentString() << std::endl;
		}
	}
}

void PnLManagerAgent::updateOnFill(const std::string& owner, const Money& fill_price, Volume fill_volume, OrderDirection direction) {
	if (fill_volume == 0) return;

	long long dq = (direction == OrderDirection::Buy) ? (long long)fill_volume : -(long long)fill_volume;

	auto& s = m_states[owner]; // creates entry if missing

	// No existing position -> open new
	if (s.inventory == 0) {
		s.inventory = (int)dq;
		s.avg_price = fill_price;
		if (s.inventory != 0) m_agents_with_positions.insert(owner);
		return;
	}

	// Increasing existing position (same side)
	if ((s.inventory > 0 && dq > 0) || (s.inventory < 0 && dq < 0)) {
		int new_inventory = (int)(s.inventory + dq);
		Money numerator = s.avg_price * (int)std::llabs(s.inventory) + fill_price * (int)std::llabs(dq);
		s.avg_price = numerator / (int)std::llabs(new_inventory);
		s.inventory = new_inventory;
		if (s.inventory != 0) m_agents_with_positions.insert(owner);
		else m_agents_with_positions.erase(owner);
		return;
	}

	// Reducing or flipping
	int closing_qty = (int)std::min((long long)std::llabs(s.inventory), (long long)std::llabs(dq));
	Money pnl_close = Money(0);
	if (s.inventory > 0) { // closing long
		pnl_close = (fill_price - s.avg_price) * closing_qty;
	} else { // closing short
		pnl_close = (s.avg_price - fill_price) * closing_qty;
	}

	s.realized_pnl += pnl_close;

	int new_inventory = (int)(s.inventory + dq);

	if (new_inventory == 0) {
		// Position fully closed
		s.inventory = 0;
		s.avg_price = Money(0);
		m_agents_with_positions.erase(owner);
	} else if ((s.inventory > 0 && new_inventory < 0) || (s.inventory < 0 && new_inventory > 0)) {
		// Flipped side: remaining quantity is new position at fill_price
		s.inventory = new_inventory;
		s.avg_price = fill_price;
		m_agents_with_positions.insert(owner);
	} else {
		// Partially reduced, still same side
		s.inventory = new_inventory;
		// avg_price unchanged for remaining position
		if (s.inventory != 0) m_agents_with_positions.insert(owner);
	}
}

bool PnLManagerAgent::test_getPnLSnapshot(const std::string& owner, int& inventory, Money& avg_price, Money& realized_pnl, Money& unrealized_pnl) const {
	auto it = m_states.find(owner);
	if (it == m_states.end()) return false;
	const PnLState& s = it->second;

	inventory = s.inventory;
	avg_price = s.avg_price;
	realized_pnl = s.realized_pnl;

	Money unrealized = Money(0);
	if (s.inventory != 0 && m_last_trade_price != Money(0) && s.avg_price != Money(0)) {
		unrealized = (m_last_trade_price - s.avg_price) * s.inventory;
	}
	unrealized_pnl = unrealized;
	return true;
}
