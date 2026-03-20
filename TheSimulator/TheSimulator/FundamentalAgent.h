#pragma once

#include "Agent.h"

#include <string>

class FundamentalAgent : public Agent {
public:
    FundamentalAgent(const Simulation* simulation) : Agent(simulation) {}
    FundamentalAgent(const Simulation* simulation, const std::string& name) : Agent(simulation, name) {}

    void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
    void receiveMessage(const MessagePtr& msg) override;

private:
    std::string m_exchange;
    unsigned long long m_offset = 1;
    unsigned long long m_interval = 1;
    double m_pTrade = 0.15;

    std::string m_newsAgent = "NEWS_AGENT";
    double m_fundamentalPrice = 100.0;
    double m_recentNews = 0.0;
    double m_priceUpdateSigma = 1.0;

    double m_marketOrderThreshold = 0.1;
    double m_opinionThreshold = 0.05;
    double m_limitOrderLambda = 5.0;

    void updateFundamentalPrice();
};
