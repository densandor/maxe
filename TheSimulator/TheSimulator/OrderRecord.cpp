#include "OrderFactory.h"
#include "Order.h"

OrderFactory::OrderFactory()
	: m_orderCount(0) { }

OrderFactory::OrderFactory(OrderFactory&& orderFactory) noexcept
	: m_orderCount(orderFactory.m_orderCount) { }

OrderFactory::~OrderFactory() {
	
}

MarketOrderPtr OrderFactory::makeMarketOrder(OrderDirection direction, Timestamp timestamp, Volume volume, Owner owner) {
	++m_orderCount;

	MarketOrderPtr op = MarketOrderPtr(new MarketOrder(m_orderCount, direction, timestamp, volume, owner)); // has to be explicit because make_shared can't make use of friendships

	return op;
}

LimitOrderPtr OrderFactory::makeLimitOrder(OrderDirection direction, Timestamp timestamp, Volume volume, Owner owner, Money price) {
	++m_orderCount;

	LimitOrderPtr op = LimitOrderPtr(new LimitOrder(m_orderCount, direction, timestamp, volume, owner, price)); // has to be explicit because make_shared can't make use of friendships

	return op;
}

MarketOrderPtr OrderFactory::marketBuy(Timestamp timestamp, Volume volume, Owner owner) {
	return makeMarketOrder(OrderDirection::Buy, timestamp, volume, owner);
}

MarketOrderPtr OrderFactory::marketSell(Timestamp timestamp, Volume volume, Owner owner) {
	return makeMarketOrder(OrderDirection::Sell, timestamp, volume, owner);
}

LimitOrderPtr OrderFactory::limitBuy(Timestamp timestamp, Volume volume, Owner owner, Money price) {
	return makeLimitOrder(OrderDirection::Buy, timestamp, volume, owner, price);
}

LimitOrderPtr OrderFactory::limitSell(Timestamp timestamp, Volume volume, Owner owner, Money price) {
	return makeLimitOrder(OrderDirection::Sell, timestamp, volume, owner, price);
}

#include <iostream>