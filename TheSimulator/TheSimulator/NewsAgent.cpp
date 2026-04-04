#include "NewsAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>
#include <filesystem>

void NewsAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
    Agent::configure(node, configurationPath);

    pugi::xml_attribute att;
    if (!(att = node.attribute("offset")).empty()) {
        m_offset = std::stoull(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("mean")).empty()) {
        m_mean = std::stod(simulation()->parameters().processString(att.as_string()));
        std::cout << "NewsAgent: configured mean news value: " << m_mean << std::endl;
    }
    if (!(att = node.attribute("standardDeviation")).empty()) {
        m_standardDeviation = std::stod(simulation()->parameters().processString(att.as_string()));
        std::cout << "NewsAgent: configured standard deviation: " << m_standardDeviation << std::endl;
    }
    if (!(att = node.attribute("newsPoissonLambda")).empty()) {
        m_newsPoissonLambda = std::stod(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("mode")).empty()) {
        m_mode = simulation()->parameters().processString(att.as_string());
    }
}

void NewsAgent::receiveMessage(const MessagePtr& msg) {
    const Timestamp currentTimestamp = simulation()->currentTimestamp();

    if (msg->type == "EVENT_SIMULATION_START") {
	    simulation()->dispatchMessage(simulation()->currentTimestamp(), m_offset, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>());
        std::cout << "NewsAgent: scheduled first wake-up at timestamp " << currentTimestamp + m_offset << std::endl;
        return;
    }

    if (msg->type == "WAKE_UP") {
        unsigned long long stepsUntilNextNews = std::poisson_distribution<unsigned long long>(m_newsPoissonLambda)(simulation()->randomGenerator());
        stepsUntilNextNews = std::max(1ULL, stepsUntilNextNews);
        simulation()->dispatchMessage(simulation()->currentTimestamp(), stepsUntilNextNews, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>(), true);
        std::normal_distribution<double> normalDistribution(m_mean, m_standardDeviation);
        std::uniform_real_distribution<double> uniformDistribution(-1.0 * m_standardDeviation, m_standardDeviation);
        if (m_mode == "uniform") {
            m_news = uniformDistribution(simulation()->randomGenerator());
        } else {
            m_news = normalDistribution(simulation()->randomGenerator());
        }
        notifyNewsSubscribers();
        return;
    }

    if (msg->type == "SUBSCRIBE_NEWS") {
        if (std::binary_search(m_newsSubscribers.begin(), m_newsSubscribers.end(), msg->source)) {
            auto eretpptr = std::make_shared<ErrorResponsePayload>("The agent is already subscribed to news: " + msg->source);
            fastRespondToMessage(msg, eretpptr);
        } else {
            auto iit = std::upper_bound(m_newsSubscribers.begin(), m_newsSubscribers.end(), msg->source);
            m_newsSubscribers.insert(iit, msg->source);

            auto sretpptr = std::make_shared<SuccessResponsePayload>("Agent subscribed successfully to news: " + msg->source);
            fastRespondToMessage(msg, sretpptr);
        }
        return;
    }
}

void NewsAgent::notifyNewsSubscribers() {
	auto currentTimestamp = simulation()->currentTimestamp();
	for (const std::string& subscriber : m_newsSubscribers) {
		auto pptr = std::make_shared<NewsPayload>(m_news);
		simulation()->dispatchMessage(currentTimestamp, 0, name(), subscriber, "NEWS", pptr);
	}
}