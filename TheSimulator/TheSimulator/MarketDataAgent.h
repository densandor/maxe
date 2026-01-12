#pragma once

#include "Agent.h"

#include <string>

class MarketDataAgent : public Agent {
public:
    MarketDataAgent(const Simulation* simulation) : Agent(simulation) {}
    MarketDataAgent(const Simulation* simulation, const std::string& name) : Agent(simulation, name) {}

    void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
    void receiveMessage(const MessagePtr& msg) override;

private:
    std::string m_exchange;
    int m_demand = 0;
};
