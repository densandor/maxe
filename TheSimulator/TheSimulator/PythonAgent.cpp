#include "PythonAgent.h"
#include "Simulation.h"

#include <pybind11/stl.h>
#include <filesystem>

PythonAgent::PythonAgent(const Simulation* simulation, const std::string& pythonClass, const std::string& file)
	: Agent(simulation), m_class(pythonClass), m_file(file) { }

PythonAgent::PythonAgent(const Simulation* simulation, const std::string& name)
	: Agent(simulation, name), m_class(""), m_file("") { }

void PythonAgent::configure(const pugi::xml_node& node, const std::string& configurationPath) {
	Agent::configure(node, configurationPath);

	for (const pugi::xml_attribute& attr : node.attributes()) {
		if (std::string(attr.name()) != "file" && std::string(attr.name()) != "name") {
			m_parameters[std::string(attr.name())] = simulation()->parameters().processString(attr.as_string());
		}
	}

	// Add agents/ to sys.path so py::module::import can find modules there
	py::module sys = py::module::import("sys");
    namespace fs = std::filesystem;
    fs::path configPath = fs::absolute(configurationPath);
    fs::path repoRoot = configPath.parent_path();
    fs::path agentsDir = (repoRoot / "agents").lexically_normal();
	auto sys_path_vec = sys.attr("path").cast<std::vector<std::string>>();
    if (fs::exists(agentsDir) && std::find(sys_path_vec.begin(), sys_path_vec.end(), agentsDir.string()) == sys_path_vec.end()) {
        sys.attr("path").attr("insert")(0, agentsDir.string());
    }

	py::object agentClass;
	if (m_file == "") {
		py::module m = py::module::import(m_class.c_str());
		agentClass = m.attr(m_class.c_str());
	} else {
		py::object result = py::eval_file(m_file);
		agentClass = result.attr(m_class.c_str());
	}

	py::cpp_function nameStringFunction = [this]() {
		return this->name();
	};
	//py::object nameStringObject = py::str(name());
	m_instance = agentClass();
	m_instance.attr("name") = nameStringFunction;

	py::function fun = py::reinterpret_borrow<py::function>(m_instance.attr("configure"));
	py::object _ret = fun(m_parameters);
}

#include <iostream>

void PythonAgent::receiveMessage(const MessagePtr& msg) {
	py::function receiveMessageFunction = py::reinterpret_borrow<py::function>(m_instance.attr("receiveMessage"));
	py::object _ret = receiveMessageFunction(simulation(), msg->type, msg->payload);
}
