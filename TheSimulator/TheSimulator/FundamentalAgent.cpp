#include "FundamentalAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <random>
#include <cmath>
#include <algorithm>

void FundamentalAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
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
    if (!(att = node.attribute("pTrade")).empty()) {
        m_pTrade = std::stod(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("newsAgent")).empty()) {
        m_newsAgent = simulation()->parameters().processString(att.as_string());
    }
    if (!(att = node.attribute("fundamentalPrice")).empty()) {
        m_fundamentalPrice = std::stod(simulation()->parameters().processString(att.as_string()));
    } else {
        m_fundamentalPrice = std::uniform_real_distribution<double>(90.0, 110.0)(rng);
    }
    if (!(att = node.attribute("priceUpdateSigma")).empty()) {
        m_priceUpdateSigma = std::stod(simulation()->parameters().processString(att.as_string()));
    }
    if (!(att = node.attribute("marketOrderThreshold")).empty()) {
        m_marketOrderThreshold = std::stod(simulation()->parameters().processString(att.as_string()));
    } else {
        m_marketOrderThreshold = std::uniform_real_distribution<double>(0.005, 0.25)(rng);
    }
    if (!(att = node.attribute("opinionThreshold")).empty()) {
        m_opinionThreshold = std::stod(simulation()->parameters().processString(att.as_string()));
    } else {
        m_opinionThreshold = std::uniform_real_distribution<double>(0.01, 0.1)(rng);
    }
    if (!(att = node.attribute("limitOrderLambda")).empty()) {
        m_limitOrderLambda = std::stod(simulation()->parameters().processString(att.as_string()));
    }
}

void FundamentalAgent::updateFundamentalPrice() {
    m_fundamentalPrice += std::normal_distribution<double>(m_recentNews, m_priceUpdateSigma)(simulation()->randomGenerator());
}

void FundamentalAgent::receiveMessage(const MessagePtr& msg) {
    const Timestamp currentTimestamp = simulation()->currentTimestamp();

    if (msg->type == "EVENT_SIMULATION_START") {
        simulation()->dispatchMessage(currentTimestamp, m_offset, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>());
        simulation()->dispatchMessage(currentTimestamp, 0, name(), m_newsAgent, "SUBSCRIBE_NEWS", std::make_shared<EmptyPayload>());
        return;
    }

    if (msg->type == "WAKE_UP") {
        simulation()->dispatchMessage(currentTimestamp, m_interval, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>());

        if (std::uniform_real_distribution<double>(0.0, 1.0)(simulation()->randomGenerator()) >= m_pTrade) {
            return;
        }

        simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "RETRIEVE_L1", std::make_shared<EmptyPayload>());
        return;
    }

    if (msg->type == "RESPONSE_RETRIEVE_L1") {
        auto l1 = std::dynamic_pointer_cast<RetrieveL1ResponsePayload>(msg->payload);

        double bestAsk = static_cast<double>(l1->bestAskPrice);
        double bestBid = static_cast<double>(l1->bestBidPrice);

        double midPrice;
        if (bestAsk > 0.0 && bestBid > 0.0) {
            midPrice = (bestAsk + bestBid) / 2.0;
        } else {
            midPrice = m_fundamentalPrice;
        }

        if (std::abs(1.0 - m_fundamentalPrice / midPrice) > m_opinionThreshold) {
            if (m_fundamentalPrice >= midPrice) {
                m_fundamentalPrice = midPrice * (1.0 + m_opinionThreshold);
            } else {
                m_fundamentalPrice = midPrice * (1.0 - m_opinionThreshold);
            }
        }

        double currentFundamentalPrice = m_fundamentalPrice;

        auto& rng = simulation()->randomGenerator();

        double expSample = std::exponential_distribution<double>(m_limitOrderLambda)(rng);
        double sign = std::bernoulli_distribution(0.5)(rng) ? 1.0 : -1.0;
        double plannedPriceVal = midPrice + sign * expSample;
        plannedPriceVal = std::max(std::round(plannedPriceVal * 100.0) / 100.0, 0.01);
        Money plannedPrice(plannedPriceVal);

        if (bestAsk > 0.0 && currentFundamentalPrice > bestAsk * (1.0 + m_marketOrderThreshold)) {
            double newPrice = std::round(bestAsk * (1.0 + m_marketOrderThreshold) * std::uniform_real_distribution<double>(1.0, 1.05)(rng) * 100.0) / 100.0;
            simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "PLACE_ORDER_LIMIT", std::make_shared<PlaceOrderLimitPayload>(OrderDirection::Buy, 1, Money(newPrice)));
        } else if (bestBid > 0.0 && currentFundamentalPrice < bestBid * (1.0 - m_marketOrderThreshold)) {
            double newPrice = std::round(bestBid * (1.0 - m_marketOrderThreshold) * std::uniform_real_distribution<double>(0.95, 1.0)(rng) * 100.0) / 100.0;
            simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "PLACE_ORDER_LIMIT", std::make_shared<PlaceOrderLimitPayload>(OrderDirection::Sell, 1, Money(newPrice)));
        } else if (bestAsk > 0.0 && currentFundamentalPrice > bestAsk) {
            simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "PLACE_ORDER_LIMIT", std::make_shared<PlaceOrderLimitPayload>(OrderDirection::Buy, 1, plannedPrice));
        } else if (bestBid > 0.0 && currentFundamentalPrice < bestBid) {
            simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "PLACE_ORDER_LIMIT", std::make_shared<PlaceOrderLimitPayload>(OrderDirection::Sell, 1, plannedPrice));
        } else if (bestAsk == 0.0 && bestBid == 0.0) {
            if (currentFundamentalPrice > midPrice) {
                simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "PLACE_ORDER_LIMIT", std::make_shared<PlaceOrderLimitPayload>(OrderDirection::Buy, 1, plannedPrice));
            } else {
                simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "PLACE_ORDER_LIMIT", std::make_shared<PlaceOrderLimitPayload>(OrderDirection::Sell, 1, plannedPrice));
            }
        }
        return;
    }

    if (msg->type == "NEWS") {
        auto newsPayload = std::dynamic_pointer_cast<NewsPayload>(msg->payload);
        m_recentNews = newsPayload->news;
        updateFundamentalPrice();
        return;
    }
}
