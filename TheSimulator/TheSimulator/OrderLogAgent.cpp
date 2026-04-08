#include "OrderLogAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>
#include <filesystem>

OrderLogAgent::OrderLogAgent(const Simulation* simulation)
	: Agent(simulation) { }

OrderLogAgent::OrderLogAgent(const Simulation* simulation, const std::string& name)
	: Agent(simulation, name) { }

void OrderLogAgent::receiveMessage(const MessagePtr& messagePtr) {
	const Timestamp currentTimestamp = simulation()->currentTimestamp();

	if (messagePtr->type == "EVENT_SIMULATION_START") {
		simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "SUBSCRIBE_EVENT_ORDER_LIMIT", std::make_shared<EmptyPayload>());
		simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "SUBSCRIBE_EVENT_ORDER_MARKET", std::make_shared<EmptyPayload>());
	} else if (messagePtr->type == "EVENT_ORDER_MARKET") {
		auto pptr = std::dynamic_pointer_cast<EventOrderMarketPayload>(messagePtr->payload);
		const auto& order = pptr->order;
		// std::cout << name() << ": ";
		// order.printHuman();
		// std::cout << std::endl;
	} else if (messagePtr->type == "EVENT_ORDER_LIMIT") {
		auto pptr = std::dynamic_pointer_cast<EventOrderLimitPayload>(messagePtr->payload);
		const auto& order = pptr->order;
		// std::cout << name() << ": ";
		// order.printHuman();
		// std::cout << std::endl;
	}
}

#include "ParameterStorage.h"

void OrderLogAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
	Agent::configure(node, configurationPath);

	pugi::xml_attribute att;
	if (!(att = node.attribute("exchange")).empty()) { 
		m_exchange = simulation()->parameters().processString(att.as_string());
	}
	if (!(att = node.attribute("outputFile")).empty()) {
        std::string filename = simulation()->parameters().processString(att.as_string());
        
        // If filename doesn't contain a path separator, add logs/
        namespace fs = std::filesystem;
        fs::path filePath(filename);
        if (filePath.parent_path().empty()) {
            filePath = fs::path("logs") / filePath;
        }
        
        if (!fs::exists(filePath.parent_path())) {
            fs::create_directories(filePath.parent_path());
        }
        
        m_outputFile.open(filePath.string());

        if (m_outputFile.is_open()) {
            m_outputFile << "id,time,price,owner,direction,volume\n";
        } else {
            std::cerr << name() << ": Failed to open trade CSV file: " << att.as_string() << std::endl;
        }
    }
}