#include "L1LogAgent.h"

#include "Simulation.h"
#include "ExchangeAgentMessagePayloads.h"

#include <iostream>
#include <filesystem>

L1LogAgent::L1LogAgent(const Simulation* simulation)
	: Agent(simulation), m_exchange(""), m_interval(1), m_outputFile() { }

L1LogAgent::L1LogAgent(const Simulation* simulation, const std::string& name)
	: Agent(simulation, name), m_exchange(""), m_interval(1), m_outputFile() { }

void L1LogAgent::receiveMessage(const MessagePtr& messagePtr) {
	const Timestamp currentTimestamp = simulation()->currentTimestamp();

	if (messagePtr->type == "EVENT_SIMULATION_START") {
		simulation()->dispatchMessage(currentTimestamp, 0, name(), name(), "WAKEUP_FOR_L1_POLL", std::make_shared<EmptyPayload>(), true);
	} else if (messagePtr->type == "WAKEUP_FOR_L1_POLL") {
		simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "RETRIEVE_L1", std::make_shared<EmptyPayload>());
		simulation()->dispatchMessage(currentTimestamp, m_interval, name(), name(), "WAKEUP_FOR_L1_POLL", std::make_shared<EmptyPayload>(), true);
	} else if (messagePtr->type == "RESPONSE_RETRIEVE_L1") {
		auto pptr = std::dynamic_pointer_cast<RetrieveL1ResponsePayload>(messagePtr->payload);
		logData(pptr);
		std::cout << "T," << currentTimestamp << "," << pptr->lastTradePrice.toCentString() << std::endl;
	}
}

void L1LogAgent::logData(std::shared_ptr<RetrieveL1ResponsePayload> pptr) {
	m_outputFile << std::to_string(pptr->time) << "," << pptr->bestAskPrice.toCentString() << "," << pptr->bestAskVolume << "," << pptr->askTotalVolume << "," << pptr->bestBidPrice.toCentString() << "," << pptr->bestBidVolume << "," << pptr->bidTotalVolume << "," << pptr->lastTradePrice.toCentString() << std::endl;
}

#include "ParameterStorage.h"

void L1LogAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
	Agent::configure(node, configurationPath);

	pugi::xml_attribute att;
	if (!(att = node.attribute("exchange")).empty()) {
		m_exchange = simulation()->parameters().processString(att.as_string());
	}

	if (!(att = node.attribute("interval")).empty()) {
		m_interval = att.as_ullong();
	}

	if (!(att = node.attribute("outputFile")).empty()) {
		std::string filename = simulation()->parameters().processString(att.as_string());
        
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
			m_outputFile << "time,bestAskPrice,bestAskVolume,askTotalVolume,bestBidPrice,bestBidVolume,bidTotalVolume,lastTradePrice\n";
        } else {
            std::cerr << name() << ": Failed to open L1 CSV file: " << att.as_string() << std::endl;
        }
	}
}