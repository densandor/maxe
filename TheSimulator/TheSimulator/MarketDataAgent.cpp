#include "MarketDataAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>
#include <filesystem>

void MarketDataAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
    Agent::configure(node, configurationPath);

    pugi::xml_attribute att;
    if (!(att = node.attribute("exchange")).empty()) {
        m_exchange = simulation()->parameters().processString(att.as_string());
    }
    if (!(att = node.attribute("fastWindowSize")).empty()) {
        m_fastWindowSize = std::stoi(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("slowWindowSize")).empty()) {
        m_slowWindowSize = std::stoi(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("offset")).empty()) {
        m_offset = std::stoull(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("interval")).empty()) {
        m_interval = std::stoull(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("outputFile")).empty()) {
        std::string filename = simulation()->parameters().processString(att.as_string());
        
        namespace fs = std::filesystem;
        fs::path filePath(filename);
        if (filePath.parent_path().empty()) {
            filePath = fs::path("logs") / filePath;
        }
        
        if (!fs::exists(filePath.parent_path())) {
            fs::create_directories(filePath.parent_path());
        }
        
        m_outputFile.open(filePath.string());

        if (m_outputFile.is_open()) {
            m_outputFile << "time,price,fastEma,slowEma\n";
        } else {
            std::cerr << name() << ": Failed to open moving average CSV file: " << att.as_string() << std::endl;
        }
    }
}

void MarketDataAgent::receiveMessage(const MessagePtr& msg) {
    const Timestamp currentTimestamp = simulation()->currentTimestamp();

    if (msg->type == "EVENT_SIMULATION_START") {
	    simulation()->dispatchMessage(simulation()->currentTimestamp(), m_offset, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>(), true);
        return;
    }

    if (msg->type == "WAKE_UP") {
        simulation()->dispatchMessage(simulation()->currentTimestamp(), m_interval, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>(), true);
        simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "RETRIEVE_L1", std::make_shared<EmptyPayload>());
        return;
    }

    if (msg->type == "RESPONSE_RETRIEVE_L1") {
        auto l1 = std::dynamic_pointer_cast<RetrieveL1ResponsePayload>(msg->payload);

        double price = static_cast<double>(l1->lastTradePrice);
        
        // Store old EMAs for crossover detection
        double oldFastEma = m_fastEma;
        double oldSlowEma = m_slowEma;

        // Initialize EMAs with first price
        if (m_firstPrice) {
            m_fastEma = price;
            m_slowEma = price;
            m_firstPrice = false;
        } else {
            // Update EMAs with exponential smoothing
            double fastAlpha = 2.0 / (m_fastWindowSize + 1);
            double slowAlpha = 2.0 / (m_slowWindowSize + 1);
            m_fastEma = fastAlpha * price + (1.0 - fastAlpha) * m_fastEma;
            m_slowEma = slowAlpha * price + (1.0 - slowAlpha) * m_slowEma;
        }
        
        // Log data to CSV
        logData(currentTimestamp, price);
        
        if (oldFastEma > oldSlowEma && m_fastEma <= m_slowEma) {
            notifyMovingAverageSubscribers(Money(price), OrderDirection::Sell);
        } else if (oldFastEma < oldSlowEma && m_fastEma >= m_slowEma) {
            notifyMovingAverageSubscribers(Money(price), OrderDirection::Buy);
        }
        return;
    }

    if (msg->type == "SUBSCRIBE_MOVING_AVERAGE") {
        if (std::binary_search(m_movingAverageSubscribers.begin(), m_movingAverageSubscribers.end(), msg->source)) {
            auto eretpptr = std::make_shared<ErrorResponsePayload>("The agent is already subscribed to moving average signals: " + msg->source);
            fastRespondToMessage(msg, eretpptr);
        } else {
            auto iit = std::upper_bound(m_movingAverageSubscribers.begin(), m_movingAverageSubscribers.end(), msg->source);
            m_movingAverageSubscribers.insert(iit, msg->source);

            auto sretpptr = std::make_shared<SuccessResponsePayload>("Agent subscribed successfully to moving average signals: " + msg->source);
            fastRespondToMessage(msg, sretpptr);
        }
        return;
    }
}

void MarketDataAgent::logData(Timestamp timestamp, double price) {
    if (m_outputFile.is_open()) {
        m_outputFile << timestamp << "," << price << "," << m_fastEma << "," << m_slowEma << std::endl;
    }
}

void MarketDataAgent::notifyMovingAverageSubscribers(Money price, OrderDirection direction) {
	auto currentTimestamp = simulation()->currentTimestamp();
	for (const std::string& subscriber : m_movingAverageSubscribers) {
		auto pptr = std::make_shared<MovingAverageSignalPayload>(price, direction);
		simulation()->dispatchMessage(currentTimestamp, 0, name(), subscriber, "MOVING_AVERAGE_SIGNAL", pptr);
	}
}