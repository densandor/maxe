#pragma once

#include "Agent.h"
#include "ExchangeAgentMessagePayloads.h"

#include <fstream>
#include <unordered_map>
#include <string>

class OrderBookLogAgent : public Agent {
public:
	OrderBookLogAgent(const Simulation* simulation);
	OrderBookLogAgent(const Simulation* simulation, const std::string& name);

	void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
	void receiveMessage(const MessagePtr& msg) override;

private:
	std::string m_exchange;
	Timestamp m_interval;
	unsigned int m_depth;
	std::ofstream m_outputFile;
	std::unordered_map<std::string, Volume> m_prevBidLevels;
	std::unordered_map<std::string, Volume> m_prevAskLevels;

	void logBookSide(const std::shared_ptr<RetrieveBookResponsePayload>& payload, const char* side);
};
