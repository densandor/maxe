#include "PortfolioAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>
#include <iomanip>
#include <filesystem>
#include <algorithm>


double computeUnrealizedPnL(const PnLState& state, const Money& lastTradePrice) {
	if (state.inventory == 0 || lastTradePrice == Money(0) || state.avg_price == 0.0) {
		return 0.0;
	}
	const double lastPrice = static_cast<double>(lastTradePrice);
	return (lastPrice - state.avg_price) * state.inventory;
}


PortfolioAgent::PortfolioAgent(const Simulation* simulation)
	: Agent(simulation), m_exchange(""), m_last_trade_price(Money(0)) { }

PortfolioAgent::PortfolioAgent(const Simulation* simulation, const std::string& name)
	: Agent(simulation, name), m_exchange(""), m_last_trade_price(Money(0)) { }

void PortfolioAgent::ensureAgentHistoryAligned(const std::string& agent) {
	auto& state = m_states[agent];
	if (state.history.size() < m_sample_count) {
		state.history.resize(m_sample_count, 0.0);
	}
}

void PortfolioAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
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

void PortfolioAgent::receiveMessage(const MessagePtr& msg) {
	const Timestamp currentTimestamp = simulation()->currentTimestamp();
	
	if (msg->type == "EVENT_SIMULATION_START") {
		// subscribe to trades on configured exchange
		simulation()->dispatchMessage(currentTimestamp, currentTimestamp, name(), m_exchange, "SUBSCRIBE_EVENT_TRADE", std::make_shared<EmptyPayload>());
		// schedule first portfolio sample
		simulation()->dispatchMessage(currentTimestamp, m_sample_interval, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>(), true);
	} else if (msg->type == "WAKE_UP") {
		samplePortfolios();
		simulation()->dispatchMessage(currentTimestamp, m_sample_interval, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>(), true);
	} else if (msg->type == "EVENT_TRADE") {
		auto pptr = std::dynamic_pointer_cast<EventTradePayload>(msg->payload);
		const auto& trade = pptr->trade;

		// Update last trade price
		m_last_trade_price = trade.price();

		// Update aggressor's position
		updateOnFill(trade.aggressingOwner(), trade.price(), trade.volume(), trade.direction());

		// Update resting side's position
		if (trade.direction() == OrderDirection::Buy) {
			updateOnFill(trade.restingOwner(), trade.price(), trade.volume(), OrderDirection::Sell);
		} else {
			updateOnFill(trade.restingOwner(), trade.price(), trade.volume(), OrderDirection::Buy);
		}

	} else if (msg->type == "REQUEST_PNL") {
		// Respond to a PnL snapshot request
		const std::string requester = msg->source;

		int inventory = 0;
		double avg_price = 0.0;
		double realized = 0.0;
		double unrealized = 0.0;
		double lastPrice = (double) m_last_trade_price;

		auto agent_state_pair = m_states.find(requester);
		if (agent_state_pair != m_states.end()) {
			const PnLState& state = agent_state_pair->second;
			inventory = state.inventory;
			avg_price = state.avg_price;
			realized = state.realized_pnl;
			unrealized = computeUnrealizedPnL(state, m_last_trade_price);
		}

		auto resp = std::make_shared<ResponsePnLPayload>(inventory, avg_price, realized, unrealized, lastPrice);
		simulation()->dispatchMessage(currentTimestamp, 0, name(), requester, "RESPONSE_PNL", resp);

	} else if (msg->type == "EVENT_SIMULATION_STOP") {
		// Final sample at simulation end
		samplePortfolios();
		// Write portfolio history CSV
		writePortfolioCSV();
	}
}

void PortfolioAgent::updateOnFill(const std::string& owner, const Money& fill_price, Volume fill_volume, OrderDirection direction) {
	
	const int signed_volume = (direction == OrderDirection::Buy) ? static_cast<int>(fill_volume) : -static_cast<int>(fill_volume);
	const double fill_price_d = static_cast<double>(fill_price);

	// Find the PnLState for the agent, creating one if it doesn't exist
	auto& state = m_states[owner];
	// Keep the length of the history vector aligned with the number of samples taken so far
	ensureAgentHistoryAligned(owner);

	const int old_inventory = state.inventory;

	// Case 1: Opening a new position
	if (old_inventory == 0) {
		state.inventory = signed_volume;
		state.avg_price = fill_price_d;
		return;
	}

	const int new_inventory = old_inventory + signed_volume;

	// Case 2: Increasing existing position
	if ((state.inventory > 0 && signed_volume > 0) || (state.inventory < 0 && signed_volume < 0)) {
		double total_price = state.avg_price * (int)std::llabs(state.inventory) + fill_price_d * (int)std::llabs(signed_volume);
		state.avg_price = total_price / (int)std::llabs(new_inventory);
		state.inventory = new_inventory;
		return;
	}

	// Case 3: Reducing or flipping position (updating realized PnL)
	const int volume_to_close = std::min(static_cast<int>(std::llabs(old_inventory)), static_cast<int>(std::llabs(signed_volume)));
	if (old_inventory > 0) {
		// Closing a long position (selling)
		state.realized_pnl += (fill_price_d - state.avg_price) * volume_to_close;
	} else {
		// Closing a short position (buying)
		state.realized_pnl += (state.avg_price - fill_price_d) * volume_to_close;
	}

	if (new_inventory == 0) {
		// Fully closing position
		state.inventory = 0;
		state.avg_price = 0.0;
	} else if ((state.inventory > 0 && new_inventory < 0) || (state.inventory < 0 && new_inventory > 0)) {
		// Flipping side
		state.inventory = new_inventory;
		state.avg_price = fill_price_d;
	} else {
		// Reducing position but not flipping
		state.inventory = new_inventory;
	}
}

void PortfolioAgent::samplePortfolios() {
	for (auto& agent_state_pair : m_states) {
		PnLState& state = agent_state_pair.second;
		state.history.push_back(state.realized_pnl + computeUnrealizedPnL(state, m_last_trade_price));
	}
	++m_sample_count;
}

void PortfolioAgent::writePortfolioCSV() {
	std::ofstream out(m_portfolio_output_file);

	// Sort agent names for stable column order
	std::vector<std::string> agents;
	agents.reserve(m_states.size());
	for (const auto& kv : m_states) {
		agents.push_back(kv.first);
	}
	std::sort(agents.begin(), agents.end());

	// Log header containing time, agent1, agent2, ...
	out << "time";
	for (const auto& agent : agents) {
		out << "," << agent;
	}
	out << "\n";

	// Log portfolio values for each agent for each sample time
	Timestamp sample_time = m_sample_interval;
	for (int row = 0; row < m_sample_count; row++) {
		out << sample_time;
		for (const auto& agent : agents) {
			const auto agent_state_pair = m_states.find(agent);
			const PnLState& state = agent_state_pair->second;
			out << "," << std::fixed << std::setprecision(6) << state.history[row];
		}
		out << "\n";
		sample_time += m_sample_interval;
	}

	out.close();
}
