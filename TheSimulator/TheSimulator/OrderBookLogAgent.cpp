#include "OrderBookLogAgent.h"

#include "Simulation.h"

#include <filesystem>
#include <iostream>

OrderBookLogAgent::OrderBookLogAgent(const Simulation* simulation)
	: Agent(simulation), m_exchange(""), m_interval(1), m_depth(100), m_outputFile() { }

OrderBookLogAgent::OrderBookLogAgent(const Simulation* simulation, const std::string& name)
	: Agent(simulation, name), m_exchange(""), m_interval(1), m_depth(100), m_outputFile() { }

void OrderBookLogAgent::receiveMessage(const MessagePtr& msg) {
	const Timestamp currentTimestamp = simulation()->currentTimestamp();

	if (msg->type == "EVENT_SIMULATION_START") {
		simulation()->dispatchMessage(currentTimestamp, 0, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>(), true);
	} else if (msg->type == "WAKE_UP") {
		auto payload = std::make_shared<RetrieveBookPayload>(m_depth);
		simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "RETRIEVE_BOOK_BID", payload);
		simulation()->dispatchMessage(currentTimestamp, 0, name(), m_exchange, "RETRIEVE_BOOK_ASK", payload);
		simulation()->dispatchMessage(currentTimestamp, m_interval, name(), name(), "WAKE_UP", std::make_shared<EmptyPayload>(), true);
	} else if (msg->type == "RESPONSE_RETRIEVE_BOOK_BID") {
		auto pptr = std::dynamic_pointer_cast<RetrieveBookResponsePayload>(msg->payload);
		logBookSide(pptr, "B");
	} else if (msg->type == "RESPONSE_RETRIEVE_BOOK_ASK") {
		auto pptr = std::dynamic_pointer_cast<RetrieveBookResponsePayload>(msg->payload);
		logBookSide(pptr, "A");
	}
}

void OrderBookLogAgent::logBookSide(const std::shared_ptr<RetrieveBookResponsePayload>& payload, const char* side) {
	auto* prevLevels = (side[0] == 'B') ? &m_prevBidLevels : &m_prevAskLevels;
	std::unordered_map<std::string, Volume> nextLevels;
	nextLevels.reserve(payload->tickContainers.size());

	for (const auto& level : payload->tickContainers) {
		const Volume levelVolume = level.volume();
		if (levelVolume == 0) {
			continue;
		}

		const std::string price = level.price().toCentString();
		nextLevels[price] = levelVolume;

		std::cout
			<< "B," << payload->time << "," << side << ","
			<< price << ","
			<< levelVolume
			<< std::endl;

		if (m_outputFile.is_open()) {
			m_outputFile
				<< payload->time << ","
				<< side << ","
				<< price << ","
				<< levelVolume
				<< std::endl;
		}
	}

	for (const auto& prev : *prevLevels) {
		if (nextLevels.count(prev.first) == 0) {
			std::cout
				<< "B," << payload->time << "," << side << ","
				<< prev.first << ",0"
				<< std::endl;

			if (m_outputFile.is_open()) {
				m_outputFile
					<< payload->time << ","
					<< side << ","
					<< prev.first << ",0"
					<< std::endl;
			}
		}
	}

	*prevLevels = std::move(nextLevels);
}

#include "ParameterStorage.h"

void OrderBookLogAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
	Agent::configure(node, configurationPath);

	pugi::xml_attribute att;
	if (!(att = node.attribute("exchange")).empty()) {
		m_exchange = simulation()->parameters().processString(att.as_string());
	}

	if (!(att = node.attribute("interval")).empty()) {
		m_interval = att.as_ullong();
	}

	if (!(att = node.attribute("depth")).empty()) {
		m_depth = att.as_uint();
	}

	if (!(att = node.attribute("outputFile")).empty()) {
		std::string filename = simulation()->parameters().processString(att.as_string());

		namespace fs = std::filesystem;
		fs::path filePath(filename);
		if (filePath.parent_path().empty()) {
			filePath = fs::path("logs") / filePath;
		}

		m_outputFile.open(filePath.string());
		if (m_outputFile.is_open()) {
			m_outputFile << "time,side,price,volume\n";
		} else {
			std::cerr << name() << ": Failed to open order book CSV file: " << att.as_string() << std::endl;
		}
	}
}
