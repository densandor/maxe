#include "MarketDataAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>

void MarketDataAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
    Agent::configure(node, configurationPath);

    pugi::xml_attribute att;
    if (!(att = node.attribute("exchange")).empty()) {
        m_exchange = simulation()->parameters().processString(att.as_string());
    }
}

void MarketDataAgent::receiveMessage(const MessagePtr& msg) {
    const Timestamp currentTimestamp = simulation()->currentTimestamp();

    if (msg->type == "EVENT_SIMULATION_START") {
        // subscribe to market order events on configured exchange
        simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "SUBSCRIBE_EVENT_ORDER_MARKET", std::make_shared<EmptyPayload>());
        return;
    }

    if (msg->type == "EVENT_ORDER_MARKET") {
        auto pptr = std::dynamic_pointer_cast<EventOrderMarketPayload>(msg->payload);
        if (!pptr) return;

        const MarketOrder& order = pptr->order;
        // accumulate signed demand: buys positive, sells negative
        if (order.direction() == OrderDirection::Buy) {
            m_demand += static_cast<int>(order.volume());
        } else {
            m_demand -= static_cast<int>(order.volume());
        }
        return;
    }

    if (msg->type == "REQUEST_MARKET_DATA") {
        // Respond with accumulated demand and reset it for the next period
        auto resp = std::make_shared<ResponseMarketDataPayload>(m_demand);
        // reset after reporting (behaviour mirrors per-period accumulation)
        m_demand = 0;
        simulation()->dispatchMessage(currentTimestamp, 0, name(), msg->source, "RESPONSE_REQUEST_MARKET_DATA", resp);
        return;
    }
}
