#pragma once

#include "IHumanPrintable.h"
#include "ICSVPrintable.h"
#include "Order.h"

#include <memory>
#include <map>
#include <list>

class OrderFactory {
public:
	OrderFactory();
	OrderFactory(const OrderFactory& orderFactory) = default;
	OrderFactory(OrderFactory&& orderFactory) noexcept;
	~OrderFactory();

	MarketOrderPtr makeMarketOrder(OrderDirection direction, Timestamp timestamp, Volume volume, Owner owner);
	LimitOrderPtr makeLimitOrder(OrderDirection direction, Timestamp timestamp, Volume volume, Owner owner, Money price);

	// convenience methods
	MarketOrderPtr marketBuy(Timestamp timestamp, Volume volume, Owner owner);
	MarketOrderPtr marketSell(Timestamp timestamp, Volume volume, Owner owner);
	LimitOrderPtr limitBuy(Timestamp timestamp, Volume volume, Owner owner, Money price);
	LimitOrderPtr limitSell(Timestamp timestamp, Volume volume, Owner owner, Money price);
private:
	OrderID m_orderCount;
};
using OrderFactoryPtr = std::shared_ptr<OrderFactory>;

