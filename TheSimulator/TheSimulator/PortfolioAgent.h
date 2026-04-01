#pragma once

#include "Agent.h"
#include "Trade.h"
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <fstream>

struct PnLState {
	int inventory = 0; // signed position
	double avg_price = 0.0;  // average entry price (float representation)
	double realized_pnl = 0.0;
};

class PortfolioAgent : public Agent {
public:
	PortfolioAgent(const Simulation* simulation);
	PortfolioAgent(const Simulation* simulation, const std::string& name);

	void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
	void receiveMessage(const MessagePtr& msg) override;

private:
	void updateOnFill(const std::string& owner, const Money& price, Volume volume, OrderDirection direction);
	void samplePortfolios(Timestamp t);
	void writePortfolioCSV();

	std::string m_exchange;
	std::unordered_map<std::string, PnLState> m_states;
	std::unordered_set<std::string> m_agents_with_positions;
	Money m_last_trade_price;

	Timestamp m_sample_interval = 1;
	std::unordered_map<std::string, std::vector<double>> m_portfolio_history;
	std::string m_portfolio_output_file = "logs/PortfolioLog.csv";
};
