#include "TradeFactory.h"

TradeFactory::TradeFactory()
	: m_tradeCount(0) { }

TradePtr TradeFactory::makeRecord(Timestamp timestamp, OrderDirection direction, OrderID aggressingOrder, Owner aggressingOwner, OrderID restingOrder, Owner restingOwner, Volume volume, Money price) {
	++m_tradeCount;

	TradePtr ret = std::make_shared<Trade>(m_tradeCount, timestamp, direction, aggressingOrder, aggressingOwner, restingOrder, restingOwner, volume, price);

	return ret;
}