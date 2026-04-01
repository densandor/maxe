#pragma once
#include "Agent.h"

#include <memory>
#include <fstream>
#include "ExchangeAgentMessagePayloads.h"

class L1LogAgent : public Agent {
public:
	L1LogAgent(const Simulation* simulation);
	L1LogAgent(const Simulation* simulation, const std::string& name);

	void configure(const pugi::xml_node& node, const std::string& configurationPath);

	// Inherited via Agent
	void receiveMessage(const MessagePtr& msg) override;
private:
	std::string m_exchange;
	Timestamp m_interval;
	std::ofstream m_outputFile;
	void logData(std::shared_ptr<RetrieveL1ResponsePayload> l1data);
};
