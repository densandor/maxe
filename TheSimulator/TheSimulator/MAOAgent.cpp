#include "MAOAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <random>
#include <cmath>

void MAOAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
    Agent::configure(node, configurationPath);

    auto& rng = simulation()->randomGenerator();

    pugi::xml_attribute att;
    if (!(att = node.attribute("exchange")).empty()) {
        m_exchange = simulation()->parameters().processString(att.as_string());
    }
    if (!(att = node.attribute("offset")).empty()) {
        m_offset = std::stoull(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("interval")).empty()) {
        m_interval = std::stoull(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("pnlAgent")).empty()) {
        m_pnlAgent = simulation()->parameters().processString(att.as_string());
    }
    if (!(att = node.attribute("marketDataAgent")).empty()) {
        m_marketDataAgent = simulation()->parameters().processString(att.as_string());
    }
    if (!(att = node.attribute("profitFactor")).empty()) {
        m_profitFactor = std::stod(simulation()->parameters().processString(att.as_string()));
    } else {
        m_profitFactor = std::uniform_real_distribution<double>(0.01, 0.2)(rng);
    }
    if (!(att = node.attribute("waitTime")).empty()) {
        m_waitTime = std::stoull(simulation()->parameters().processString(att.as_string()));
    } else {
        m_waitTime = static_cast<unsigned long long>(std::uniform_real_distribution<double>(0.0, 20.0)(rng));
    }
}

void MAOAgent::receiveMessage(const MessagePtr& msg) {
    const Timestamp currentTimestamp = simulation()->currentTimestamp();

    if (msg->type == "EVENT_SIMULATION_START") {
        simulation()->dispatchMessage(currentTimestamp, 0, name(), m_marketDataAgent, "SUBSCRIBE_MOVING_AVERAGE", std::make_shared<EmptyPayload>());
        simulation()->dispatchMessage(currentTimestamp, m_offset, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>());
        return;
    }

    if (msg->type == "WAKE_UP") {
        simulation()->dispatchMessage(currentTimestamp, m_interval, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>());
        simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "RETRIEVE_L1", std::make_shared<EmptyPayload>());
        return;
    }

    if (msg->type == "RESPONSE_RETRIEVE_L1") {
        auto l1 = std::dynamic_pointer_cast<RetrieveL1ResponsePayload>(msg->payload);
        m_lastTradePrice = static_cast<double>(l1->lastTradePrice);
        m_hasLastTradePrice = true;
        simulation()->dispatchMessage(currentTimestamp, 0, name(), m_pnlAgent, "REQUEST_PNL", std::make_shared<EmptyPayload>());
        return;
    }

    if (msg->type == "RESPONSE_PNL") {
        auto pnl = std::dynamic_pointer_cast<ResponsePnLPayload>(msg->payload);
        int inventory = pnl->inventory;
        double avgPrice = pnl->avgPrice;

        double profitTargetPrice = 0.0;
        if (inventory > 0) {
            profitTargetPrice = avgPrice * (1.0 + m_profitFactor);
        } else if (inventory < 0) {
            profitTargetPrice = avgPrice * (1.0 - m_profitFactor);
        }

        if (inventory > 0 && m_lastTradePrice > profitTargetPrice) {
            Volume vol = static_cast<Volume>(std::floor(std::abs(static_cast<double>(inventory))));
            simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "PLACE_ORDER_MARKET", std::make_shared<PlaceOrderMarketPayload>(OrderDirection::Sell, vol));
        }
        if (inventory < 0 && m_lastTradePrice < profitTargetPrice) {
            Volume vol = static_cast<Volume>(std::floor(std::abs(static_cast<double>(inventory))));
            simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "PLACE_ORDER_MARKET", std::make_shared<PlaceOrderMarketPayload>(OrderDirection::Buy, vol));
        }
        return;
    }

    if (msg->type == "MOVING_AVERAGE_SIGNAL") {
        auto signal = std::dynamic_pointer_cast<MovingAverageSignalPayload>(msg->payload);
        simulation()->dispatchMessage(currentTimestamp, m_waitTime, name(), m_exchange, "PLACE_ORDER_MARKET", std::make_shared<PlaceOrderMarketPayload>(signal->direction, 1));
        return;
    }
}
