#pragma once

#include "Agent.h"

#include <string>
#include <list>

class NewsAgent : public Agent {
public:
    NewsAgent(const Simulation* simulation) : Agent(simulation) {}
    NewsAgent(const Simulation* simulation, const std::string& name) : Agent(simulation, name) {}

    void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
    void receiveMessage(const MessagePtr& msg) override;

private:
    unsigned long long m_offset = 1;
    unsigned long long m_newsPoissonLambda = 100;
    std::string m_mode = "normal";

    double m_mean = 0.0;
    double m_standardDeviation = 0.5;
    double m_news = 0.0;

    std::list<std::string> m_newsSubscribers;

    void notifyNewsSubscribers();
};
