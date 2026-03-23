#include "PnLManagerAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>
#include <iomanip>
#include <filesystem>
#include <algorithm>

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

	if (!(att = node.attribute("sampleInterval")).empty()) {
		m_sample_interval = att.as_ullong();
	}

	if (!(att = node.attribute("portfolioOutputFile")).empty()) {
		m_portfolio_output_file = simulation()->parameters().processString(att.as_string());
		namespace fs = std::filesystem;
		fs::path filePath(m_portfolio_output_file);
		if (filePath.parent_path().empty()) {
			m_portfolio_output_file = (fs::path("logs") / filePath).string();
		}
	}
}

void PnLManagerAgent::receiveMessage(const MessagePtr& msg) {
	const Timestamp currentTimestamp = simulation()->currentTimestamp();
	
	if (msg->type == "EVENT_SIMULATION_START") {
		// subscribe to trades on configured exchange
		simulation()->dispatchMessage(currentTimestamp, currentTimestamp, name(), m_exchange, "SUBSCRIBE_EVENT_TRADE", std::make_shared<EmptyPayload>());
		// schedule first portfolio sample
		simulation()->dispatchMessage(currentTimestamp, m_sample_interval, name(), name(), "WAKEUP_SAMPLE_PORTFOLIOS", std::make_shared<EmptyPayload>());
	} else if (msg->type == "WAKEUP_SAMPLE_PORTFOLIOS") {
		samplePortfolios(currentTimestamp);
		simulation()->dispatchMessage(currentTimestamp, m_sample_interval, name(), name(), "WAKEUP_SAMPLE_PORTFOLIOS", std::make_shared<EmptyPayload>());
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
		double avg_price = 0.0;
		double realized = 0.0;
		double unrealized = 0.0;
		double lastPrice = (double)m_last_trade_price;

		auto it = m_states.find(requester);
		if (it != m_states.end()) {
			const PnLState& s = it->second;
			inventory = s.inventory;
			avg_price = s.avg_price;
			realized = s.realized_pnl;
			if (s.inventory != 0 && m_last_trade_price != Money(0) && s.avg_price != 0.0) {
				unrealized = (lastPrice - s.avg_price) * s.inventory;
			}
		}

		auto resp = std::make_shared<ResponsePnLPayload>(inventory, avg_price, realized, unrealized, lastPrice);
		simulation()->dispatchMessage(currentTimestamp, 0, name(), requester, "RESPONSE_PNL", resp);

	} else if (msg->type == "EVENT_SIMULATION_STOP") {
		// Final sample at simulation end
		samplePortfolios(currentTimestamp);
		// Write portfolio history CSV
		writePortfolioCSV();
		// Snapshot and print final per-agent stats (lazy MTM)
		// std::cout << "\n=== Final PnL summary (agent, inventory, avg_price, realized_pnl, unrealized_pnl, last_price) ===\n";
		// for (const auto& kv : m_states) {
		// 	const std::string& agent = kv.first;
		// 	const PnLState& s = kv.second;

		// 	double unrealized = 0.0;
		// 	double lastPrice = (double)m_last_trade_price;
		// 	if (s.inventory != 0 && m_last_trade_price != Money(0) && s.avg_price != 0.0) {
		// 		unrealized = (lastPrice - s.avg_price) * s.inventory;
		// 	}

		// 	std::cout << agent << ", "
		// 		<< s.inventory << ", " << std::fixed << std::setprecision(6) << s.avg_price << ", "
		// 		<< std::fixed << std::setprecision(6) << s.realized_pnl << ", " << unrealized << ", " << lastPrice << std::endl;
		// }
	}
}

void PnLManagerAgent::updateOnFill(const std::string& owner, const Money& fill_price, Volume fill_volume, OrderDirection direction) {
	if (fill_volume == 0) return;

	long long dq = (direction == OrderDirection::Buy) ? (long long)fill_volume : -(long long)fill_volume;

	auto& s = m_states[owner]; // creates entry if missing

	double fill_price_d = static_cast<double>(fill_price);

	// No existing position -> open new
	if (s.inventory == 0) {
		s.inventory = (int)dq;
		s.avg_price = fill_price_d;
		if (s.inventory != 0) m_agents_with_positions.insert(owner);
		return;
	}

	// Increasing existing position (same side)
	if ((s.inventory > 0 && dq > 0) || (s.inventory < 0 && dq < 0)) {
		int new_inventory = (int)(s.inventory + dq);
		double numerator = s.avg_price * (int)std::llabs(s.inventory) + fill_price_d * (int)std::llabs(dq);
		s.avg_price = numerator / (int)std::llabs(new_inventory);
		s.inventory = new_inventory;
		if (s.inventory != 0) m_agents_with_positions.insert(owner);
		else m_agents_with_positions.erase(owner);
		return;
	}

	// Reducing or flipping
	int closing_qty = (int)std::min((long long)std::llabs(s.inventory), (long long)std::llabs(dq));
	double pnl_close = 0.0;
	if (s.inventory > 0) { // closing long
		pnl_close = (fill_price_d - s.avg_price) * closing_qty;
	} else { // closing short
		pnl_close = (s.avg_price - fill_price_d) * closing_qty;
	}

	s.realized_pnl += pnl_close;

	int new_inventory = (int)(s.inventory + dq);

	if (new_inventory == 0) {
		// Position fully closed
		s.inventory = 0;
		s.avg_price = 0.0;
		m_agents_with_positions.erase(owner);
	} else if ((s.inventory > 0 && new_inventory < 0) || (s.inventory < 0 && new_inventory > 0)) {
		// Flipped side: remaining quantity is new position at fill_price
		s.inventory = new_inventory;
		s.avg_price = fill_price_d;
		m_agents_with_positions.insert(owner);
	} else {
		// Partially reduced, still same side
		s.inventory = new_inventory;
		// avg_price unchanged for remaining position
		if (s.inventory != 0) m_agents_with_positions.insert(owner);
	}
}

void PnLManagerAgent::samplePortfolios(Timestamp t) {
	double lastPrice = (double)m_last_trade_price;

	for (const auto& kv : m_states) {
		const std::string& agent = kv.first;
		const PnLState& s = kv.second;

		double unrealized = 0.0;
		if (s.inventory != 0 && m_last_trade_price != Money(0) && s.avg_price != 0.0) {
			unrealized = (lastPrice - s.avg_price) * s.inventory;
		}

		double value = s.realized_pnl + unrealized;
		m_portfolio_history[agent].push_back(value);
	}
}

void PnLManagerAgent::writePortfolioCSV() {
	std::ofstream out(m_portfolio_output_file);
	if (!out.is_open()) {
		std::cerr << name() << ": Failed to open portfolio CSV: " << m_portfolio_output_file << std::endl;
		return;
	}

	// collect and sort agent names for stable column order
	std::vector<std::string> agents;
	agents.reserve(m_portfolio_history.size());
	for (const auto& kv : m_portfolio_history) {
		agents.push_back(kv.first);
	}
	std::sort(agents.begin(), agents.end());

	// header: time, agent1, agent2, ...
	out << "time";
	for (const auto& a : agents) {
		out << "," << a;
	}
	out << "\n";

	// one row per sample, timestamp computed from sample_interval
	size_t max_rows = 0;
	for (const auto& a : agents) {
		max_rows = std::max(max_rows, m_portfolio_history[a].size());
	}

	Timestamp t = m_sample_interval;
	for (size_t row = 0; row < max_rows; ++row) {
		out << t;
		for (const auto& a : agents) {
			const auto& history = m_portfolio_history[a];
			if (row < history.size()) {
			out << "," << std::fixed << std::setprecision(6) << history[row];
			} else {
				out << ",0.000000";
			}
		}
		out << "\n";
		t += m_sample_interval;
	}

	out.close();
	std::cout << name() << ": Portfolio history written to " << m_portfolio_output_file << std::endl;
}
