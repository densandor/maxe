#pragma once

#include <memory>
#include <map>
#include <string>
#include "Order.h"

struct MessagePayload {
	virtual ~MessagePayload() = default; // for this type to be polymorphic
protected:
	MessagePayload() = default;
};
using MessagePayloadPtr = std::shared_ptr<MessagePayload>;

struct ErrorResponsePayload : public MessagePayload {
	std::string message;

	ErrorResponsePayload(const std::string& message) : message(message) { }
};

struct SuccessResponsePayload : public MessagePayload {
	std::string message;

	SuccessResponsePayload(const std::string& message) : message(message) { }
};

struct EmptyPayload : public MessagePayload {

};

struct GenericPayload : public MessagePayload, public std::map<std::string, std::string> {
	GenericPayload(const std::map<std::string, std::string>& initMap)
		: MessagePayload(), std::map<std::string, std::string>(initMap) { }
};

struct ResponsePnLPayload : public MessagePayload {
	int inventory;
	double avgPrice;
	double realizedPnl;
	double unrealizedPnl;
	double lastPrice;

	ResponsePnLPayload(int inventory, double avgPrice, double realizedPnl, double unrealizedPnl, double lastPrice)
		: inventory(inventory), avgPrice(avgPrice), realizedPnl(realizedPnl), unrealizedPnl(unrealizedPnl), lastPrice(lastPrice) { }
};

struct MovingAverageSignalPayload : public MessagePayload {
	Money price;
	OrderDirection direction;

	MovingAverageSignalPayload(Money price, OrderDirection direction) : price(price), direction(direction) {}
};

struct NewsPayload : public MessagePayload {
	double news;

	NewsPayload(double news) : news(news) {}
};