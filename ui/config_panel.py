import imgui
from pathlib import Path


class ConfigPanel:
    def __init__(self, sim_manager, chart_panel, stats_panel=None, market_panel=None):
        self.sim_manager = sim_manager
        self.chart_panel = chart_panel
        self.stats_panel = stats_panel
        self.market_panel = market_panel
        self.agent_count = 5
        self.simulation_files = []
        self.selected_simulation = 0
        self._load_simulation_files()

    def _load_simulation_files(self):
        simulations_dir = Path(__file__).parent.parent / "simulations"
        if simulations_dir.exists():
            self.simulation_files = sorted([
                f.name for f in simulations_dir.glob("*.xml")
            ])
        if not self.simulation_files:
            self.simulation_files = ["No simulations found"]

    def render(self):
        imgui.set_next_window_position(20, 20, imgui.FIRST_USE_EVER)
        imgui.set_next_window_size(250, 200, imgui.FIRST_USE_EVER)

        if imgui.begin("Configuration"):
            imgui.text("Simulation Config")

            # Simulation file selector
            changed, self.selected_simulation = imgui.combo(
                "Simulation",
                self.selected_simulation,
                self.simulation_files
            )

            sim_running = self.sim_manager.is_running()

            if not sim_running and imgui.button("Start Simulation", 320, 30):
                self.chart_panel.clear()
                if self.stats_panel:
                    self.stats_panel.clear()
                if self.market_panel:
                    self.market_panel.clear()
                selected_file = self.simulation_files[self.selected_simulation]
                if self.sim_manager.start_simulation(selected_file):
                    print(f"Simulation started using {selected_file}")

            if sim_running and imgui.button("Stop Simulation", 320, 30):
                self.sim_manager.stop_simulation()

            status = "Running" if sim_running else "Stopped"
            imgui.text(f"Status: {status}")
            imgui.end()
