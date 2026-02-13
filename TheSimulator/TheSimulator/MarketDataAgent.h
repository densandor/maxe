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
    int m_fastMaoWindow = 12;
    int m_slowMaoWindow = 26;
    double m_fastEma = 0.0;
    double m_slowEma = 0.0;
    bool m_firstPrice = true;
};
