import imgui


class ConfigPanel:
    def __init__(self, sim_manager, chart_panel):
        self.sim_manager = sim_manager
        self.chart_panel = chart_panel
        self.agent_count = 5

    def render(self):
        imgui.set_next_window_position(20, 20, imgui.FIRST_USE_EVER)
        imgui.set_next_window_size(250, 200, imgui.FIRST_USE_EVER)

        if imgui.begin("Configuration"):
            imgui.text("Simulation Config")
            changed, self.agent_count = imgui.slider_int("Agents", self.agent_count, 1, 20)

            sim_running = self.sim_manager.is_running()

            if not sim_running and imgui.button("Start Simulation", 200, 30):
                self.chart_panel.clear()
                if self.sim_manager.start_simulation("20RandomAgents.xml"):
                    print(f"Simulation started with {self.agent_count} agents")

            if sim_running and imgui.button("Stop Simulation", 200, 30):
                self.sim_manager.stop_simulation()

            status = "Running" if sim_running else "Stopped"
            imgui.text(f"Status: {status}")
            imgui.end()
