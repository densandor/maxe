#include "Order.h"

#include <iostream>

void BasicOrder::printHuman() const {
	std::cout << m_id << ":\t" << m_timestamp << "\t" << m_volume;
}

void BasicOrder::printCSV() const {
	std::cout << m_id << "," << m_timestamp << "," << m_volume;
}

BasicOrder::BasicOrder(OrderID id, Timestamp timestamp, Volume orderVolume)
	: m_id(id), m_timestamp(timestamp), m_volume(orderVolume) { }

Order::Order(const Order& order)
	: BasicOrder(order), m_direction(order.m_direction), m_owner(order.m_owner) { }

Order::Order(Order&& order)
	: BasicOrder(order), m_direction(order.m_direction), m_owner(order.m_owner) { }

void Order::printHuman() const {
	this->BasicOrder::printHuman();

	std::cout << "\t" << (m_direction == OrderDirection::Buy ? "buy" : "sell") << "\t" << m_owner;
}

void Order::printCSV() const {
	this->BasicOrder::printCSV();

	std::cout << "," << (m_direction == OrderDirection::Buy ? "buy" : "sell") << "\t" << m_owner;
}

Order::Order(OrderID id, OrderDirection direction, Timestamp timestamp, Volume volume, Owner owner)
	: BasicOrder(id, timestamp, volume), m_direction(direction), m_owner(owner) {
}

void MarketOrder::printHuman() const {
	this->BasicOrder::printHuman();

	std::cout << "\tMKT" << std::endl;
}

void MarketOrder::printCSV() const { 
	this->BasicOrder::printCSV();

	std::cout << ",MKT" << std::endl;
}

MarketOrder::MarketOrder(OrderID id, OrderDirection direction, Timestamp timestamp, Volume volume, Owner owner)
	: Order(id, direction, timestamp, volume, owner) {
	
}

LimitOrder::LimitOrder(OrderID id, OrderDirection direction, Timestamp timestamp, Volume volume, Owner owner, const Money& price)
	: Order(id, direction, timestamp, volume, owner), m_price(price) {
}

void LimitOrder::printHuman() const {
	this->BasicOrder::printHuman();

	std::cout << "\tLMT\t" << m_price.toCentString() << std::endl; // note this, outputting just cents
}

void LimitOrder::printCSV() const {
	this->BasicOrder::printCSV();

	std::cout << ",LMT," << m_price.toFullString() << std::endl;
}
