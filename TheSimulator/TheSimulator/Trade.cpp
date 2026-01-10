#include "Trade.h"

Trade::Trade(TradeID id, Timestamp timestamp, OrderDirection direction, OrderID aggressingOrderID, Owner aggressingOwner, OrderID restingOrderID, Owner restingOwner, Volume volume, Money price)
	: m_id(id), m_timestamp(timestamp), m_direction(direction), m_aggressingOrderID(aggressingOrderID), m_aggressingOwner(aggressingOwner), m_restingOrderID(restingOrderID), m_restingOwner(restingOwner), m_volume(volume), m_price(price) { }

#include <iostream>

void Trade::printHuman() const {
	std::cout << "Trade " + std::to_string(m_id)
		<< " occurred at time " << std::to_string(m_timestamp)
		<< ", matching order " << std::to_string(m_aggressingOrderID) 
		<< "(by " << m_aggressingOwner
		<< ") vs. " << std::to_string(m_restingOrderID) 
		<< "(by " << m_restingOwner
		<< ") (written in the " << (m_direction == OrderDirection::Sell ? "SELL" : "BUY ") << " direction)"
		<< " with volume " << std::to_string(m_volume)
		<< " and price " << m_price.toCentString();
}

void Trade::printCSV() const {
	std::cout << std::to_string(m_id) << ","
		<< std::to_string(m_timestamp) << ","
		<< std::to_string(m_aggressingOrderID) << ","
		// << m_aggressingOwner << ","
		<< (m_direction == OrderDirection::Sell ? "SELL" : "BUY") << ","
		<< std::to_string(m_restingOrderID) << ","
		// << m_restingOwner << ","
		<< std::to_string(m_volume) << ","
		<< m_price.toFullString();
}