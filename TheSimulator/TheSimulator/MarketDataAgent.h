#pragma once

#include "Agent.h"

#include <string>
#include <fstream>
#include <list>

class MarketDataAgent : public Agent {
public:
    MarketDataAgent(const Simulation* simulation) : Agent(simulation) {}
    MarketDataAgent(const Simulation* simulation, const std::string& name) : Agent(simulation, name) {}

    void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
    void receiveMessage(const MessagePtr& msg) override;

private:
    std::string m_exchange;
    unsigned long long m_offset = 1;
    unsigned long long m_interval = 1;

    int m_fastWindowSize = 100;
    int m_slowWindowSize = 200;
    double m_fastEma = 0.0;
    double m_slowEma = 0.0;
    bool m_firstPrice = true;

    std::list<std::string> m_movingAverageSubscribers;

    std::ofstream m_outputFile;
    void logData(Timestamp timestamp, double price);
    void notifyMovingAverageSubscribers(Money price, OrderDirection direction);
};
