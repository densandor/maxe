#include "TradeLogAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>
#include <filesystem>

TradeLogAgent::TradeLogAgent(const Simulation* simulation)
	: Agent(simulation) { }

TradeLogAgent::TradeLogAgent(const Simulation* simulation, const std::string& name)
	: Agent(simulation, name) { }

void TradeLogAgent::receiveMessage(const MessagePtr& messagePtr) {
	const Timestamp currentTimestamp = simulation()->currentTimestamp();
	
	if (messagePtr->type == "EVENT_SIMULATION_START") {
		simulation()->dispatchMessage(currentTimestamp, currentTimestamp, name(), m_exchange, "SUBSCRIBE_EVENT_TRADE", std::make_shared<EmptyPayload>());
	} else if (messagePtr->type == "EVENT_TRADE") {
		auto pptr = std::dynamic_pointer_cast<EventTradePayload>(messagePtr->payload);
		const auto& trade = pptr->trade;
		
		// std::cout << name() << ": ";
		// trade.printHuman();
		// std::cout << std::endl;

		// write CSV row: time, price (use Money::toCentString like L1LogAgent)
        if (m_outputFile.is_open()) {
            // adjust field access if Trade uses different member names/getters
            m_outputFile
            << std::to_string(trade.id()) << ","
            << std::to_string(trade.timestamp()) << ","
            << trade.price().toCentString() << ","
            << trade.aggressingOrderID() << ","
            << trade.aggressingOwner() << ","
            << (trade.direction() == OrderDirection::Buy ? "BUY" : "SELL") << ","
            << trade.restingOrderID() << ","
            << trade.restingOwner() << ","
            << trade.volume() << std::endl;
            m_outputFile.flush();
        }
	}
}

#include "ParameterStorage.h"

void TradeLogAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
	Agent::configure(node, configurationPath);

	pugi::xml_attribute att;
	if (!(att = node.attribute("exchange")).empty()) {
		m_exchange = simulation()->parameters().processString(att.as_string());
	}

	if (!(att = node.attribute("outputFile")).empty()) {
        std::string filename = simulation()->parameters().processString(att.as_string());
        
        // If filename doesn't contain a path separator, prepend logs/
        namespace fs = std::filesystem;
        fs::path filePath(filename);
        if (filePath.parent_path().empty()) {
            filePath = fs::path("logs") / filePath;
        }
        
        m_outputFile.open(filePath.string());

        if (m_outputFile.is_open()) {
            // header: id,time,price,agressing,direction,resting,volume
            m_outputFile << "id,time,price,aggressing,aggressingOwner,direction,resting,restingOwner,volume\n";
        } else {
            std::cerr << name() << ": Failed to open trade CSV file: " << att.as_string() << std::endl;
        }
    }
}