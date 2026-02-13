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
    if (!(att = node.attribute("fastMaoWindow")).empty()) {
        m_fastMaoWindow = std::stoi(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("slowMaoWindow")).empty()) {
        m_slowMaoWindow = std::stoi(simulation()->parameters().processString(att.as_string()));
    }
}

void MarketDataAgent::receiveMessage(const MessagePtr& msg) {
    const Timestamp currentTimestamp = simulation()->currentTimestamp();

    if (msg->type == "EVENT_SIMULATION_START") {
        // subscribe to market order events on configured exchange
        // simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "SUBSCRIBE_EVENT_ORDER_MARKET", std::make_shared<EmptyPayload>());
        simulation
        return;
    }

    // if (msg->type == "EVENT_ORDER_MARKET") {
    //     auto pptr = std::dynamic_pointer_cast<EventOrderMarketPayload>(msg->payload);
    //     if (!pptr) return;

    //     const MarketOrder& order = pptr->order;
    //     // accumulate signed demand: buys positive, sells negative
    //     if (order.direction() == OrderDirection::Buy) {
    //         m_demand += static_cast<int>(order.volume());
    //     } else {
    //         m_demand -= static_cast<int>(order.volume());
    //     }
    //     return;
    // }

    // if (msg->type == "REQUEST_MARKET_DATA") {
    //     // Respond with accumulated demand and reset it for the next period
    //     auto resp = std::make_shared<ResponseMarketDataPayload>(m_demand);
    //     // reset after reporting (behaviour mirrors per-period accumulation)
    //     m_demand = 0;
    //     simulation()->dispatchMessage(currentTimestamp, 0, name(), msg->source, "RESPONSE_REQUEST_MARKET_DATA", resp);
    //     return;
    // }

    if (msg->type == "REQUEST_MARKET_DATA") {
        // Request L1 data to calculate MAO
        simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "RETRIEVE_L1", std::make_shared<EmptyPayload>());
        return;
    }

    if (msg->type == "RESPONSE_RETRIEVE_L1") {
        auto l1 = std::dynamic_pointer_cast<RetrieveL1ResponsePayload>(msg->payload);
        if (!l1) return;

        double price = static_cast<double>(l1->lastTradePrice);
        
        // Initialize EMAs with first price
        if (m_firstPrice) {
            m_fastEma = price;
            m_slowEma = price;
            m_firstPrice = false;
        } else {
            // Update EMAs with exponential smoothing
            double fastAlpha = 2.0 / (m_fastMaoWindow + 1);
            double slowAlpha = 2.0 / (m_slowMaoWindow + 1);
            m_fastEma = fastAlpha * price + (1.0 - fastAlpha) * m_fastEma;
            m_slowEma = slowAlpha * price + (1.0 - slowAlpha) * m_slowEma;
        }

        // Calculate MAO values: (price - EMA) / EMA * 100
        double fastMao = (price - m_fastEma) / m_fastEma * 100.0;
        double slowMao = (price - m_slowEma) / m_slowEma * 100.0;

        // Respond with MAO values
        auto resp = std::make_shared<ResponseMarketDataPayload>(static_cast<int>(fastMao * 100));
        simulation()->dispatchMessage(currentTimestamp, 0, name(), msg->source, "RESPONSE_REQUEST_MAO", resp);
        return;
    }
}
