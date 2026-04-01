#pragma once

#include "Timestamp.h"
#include "Message.h"
#include "IMessageable.h"
#include "Agent.h"
#include "IConfigurable.h"
#include "ParameterStorage.h"

#include <string>
#include <queue>
#include <vector>
#include <memory>

#include <random>

#include <pybind11/embed.h>
namespace py = pybind11;

enum class SimulationState {
	INACTIVE,
	STARTED,
	STOPPED
};

struct CompareArrival {
	bool operator()(const MessagePtr& a, const MessagePtr& b) {
		if (a->arrival != b->arrival) {
			return a->arrival > b->arrival;
		}
		return a->isLogging > b->isLogging;
	}
};

class ParameterStorage;

class Simulation : public IMessageable, public IConfigurable {
public:
	Simulation(ParameterStorage* parameters);
	Simulation(ParameterStorage* parameters, Timestamp startTimestamp, Timestamp duration, const std::string& directory);
	~Simulation() = default;

	void simulate();
	void simulate(Timestamp howMuch);

	void queueMessage(const MessagePtr& messagePtr) const { m_messageQueue->push(messagePtr); }
	void dispatchMessage(Timestamp occurrence, Timestamp delay, const std::string& source, const std::string& target, const std::string& type, MessagePayloadPtr payload, bool isLogging = false) const {
		queueMessage(MessagePtr(new Message(occurrence, occurrence + delay, source, target, type, payload, isLogging)));
	}
	void dispatchGenericMessage(Timestamp occurrence, Timestamp delay, const std::string& source, const std::string& target, const std::string& type, const std::map<std::string, std::string>& payload, bool isLogging = false) const {
		queueMessage(MessagePtr(new Message(occurrence, occurrence + delay, source, target, type, std::make_unique<GenericPayload>(payload), isLogging)));
	}

	void deliverMessage(const MessagePtr& messagePtr);

	SimulationState state() const { return m_state; }
	Timestamp currentTimestamp() const { return m_currentTimestamp; }
	ParameterStorage& parameters() const { return *m_parameters; }

	std::mt19937 & randomGenerator() const { return *m_randomGenerator; };

	// Inherited via IMessageable
	virtual void receiveMessage(const MessagePtr& msg) override;

	// Inherited via IConfigurable
	virtual void configure(const pugi::xml_node& node, const std::string& configurationPath) override;
private:
	SimulationState m_state;
	void start();
	void step(Timestamp step);
	void stop();

	Timestamp m_startTimestamp;
	Timestamp m_durationTimestamp;
	Timestamp m_currentTimestamp;
	int m_lastProgressPercent;
	ParameterStorage* m_parameters;

	std::random_device m_randomDevice;
	std::unique_ptr<std::mt19937> m_randomGenerator;

	void setupChildConfiguration(const pugi::xml_node& node, const std::string& configurationPath);

	std::unique_ptr<std::priority_queue<MessagePtr, std::vector<MessagePtr>, CompareArrival>> m_messageQueue;
	std::vector<std::unique_ptr<Agent>> m_agentList;
};
