#pragma once

#include "Agent.h"
#include "Trade.h"
#include <unordered_map>
#include <string>
#include <fstream>
#include <vector>

struct PnLState {
	int inventory = 0;
	double avg_price = 0.0;
	double realized_pnl = 0.0;
	std::vector<double> history;
};

class PortfolioAgent : public Agent {
public:
	PortfolioAgent(const Simulation* simulation);
	PortfolioAgent(const Simulation* simulation, const std::string& name);

	void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
	void receiveMessage(const MessagePtr& msg) override;

private:
	void updateOnFill(const std::string& owner, const Money& price, Volume volume, OrderDirection direction);
	void samplePortfolios();
	void writePortfolioCSV();
	void ensureAgentHistoryAligned(const std::string& agent);

	std::string m_exchange;
	Timestamp m_sample_interval = 1;
	std::string m_portfolio_output_file = "logs/PortfolioLog.csv";

	size_t m_sample_count = 0;
	std::unordered_map<std::string, PnLState> m_states;
	Money m_last_trade_price;
};
