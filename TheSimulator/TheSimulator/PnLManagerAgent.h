#pragma once

#include "Agent.h"
#include "Trade.h"
#include <unordered_map>
#include <unordered_set>
#include <string>

struct PnLState {
	int inventory = 0; // signed position
	Money avg_price = Money(0);  // average entry price
	Money realized_pnl = Money(0);
};

class PnLManagerAgent : public Agent {
public:
	PnLManagerAgent(const Simulation* simulation);
	PnLManagerAgent(const Simulation* simulation, const std::string& name);

	void configure(const pugi::xml_node& node, const std::string& configurationPath) override;

	// Inherited via Agent
	void receiveMessage(const MessagePtr& msg) override;

	// Test helpers (public for unit tests)
	void test_updateOnFill(const std::string& owner, const Money& price, Volume volume, OrderDirection direction) { updateOnFill(owner, price, volume, direction); }
	void test_setLastTradePrice(const Money& p) { m_last_trade_price = p; }
	bool test_getPnLSnapshot(const std::string& owner, int& inventory, Money& avg_price, Money& realized_pnl, Money& unrealized_pnl) const;
private:
	void updateOnFill(const std::string& owner, const Money& price, Volume volume, OrderDirection direction);

	std::string m_exchange;
	std::unordered_map<std::string, PnLState> m_states;
	std::unordered_set<std::string> m_agents_with_positions;
	Money m_last_trade_price;
};
