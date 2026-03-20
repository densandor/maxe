#pragma once

#include "Agent.h"

#include <string>
#include <optional>

class MAOAgent : public Agent {
public:
    MAOAgent(const Simulation* simulation) : Agent(simulation) {}
    MAOAgent(const Simulation* simulation, const std::string& name) : Agent(simulation, name) {}

    void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
    void receiveMessage(const MessagePtr& msg) override;

private:
    std::string m_exchange;
    unsigned long long m_offset = 1;
    unsigned long long m_interval = 1;

    std::string m_pnlAgent = "PNL_AGENT";
    std::string m_marketDataAgent = "MARKET_DATA_AGENT";

    double m_profitFactor = 0.1;
    unsigned long long m_waitTime = 0;

    double m_lastTradePrice = 0.0;
    bool m_hasLastTradePrice = false;
};
