import sys
import imgui
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generateSimulation import generateSimulation


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

        # Generation inputs
        self.gen_num_random = 10
        self.gen_num_fundamental = 100
        self.gen_num_mao = 150
        self.gen_num_momentum = 0
        self.gen_num_qlearning = 0
        self.gen_num_dql = 0
        self.gen_duration = 10000
        self.gen_starting_price = 10000
        self.gen_status = False

    def _load_simulation_files(self):
        simulations_dir = Path(__file__).parent.parent / "simulations"
        if simulations_dir.exists():
            self.simulation_files = sorted([
                f.name for f in simulations_dir.glob("*.xml")
            ])
        if not self.simulation_files:
            self.simulation_files = ["No simulations found"]

    def render(self):
        imgui.set_next_window_position(0, 0, imgui.ALWAYS)
        imgui.set_next_window_size(320, 720, imgui.ALWAYS)

        if imgui.begin("Configuration"):
            imgui.text("Generate Simulation")
            imgui.text("Agents")

            _, self.gen_num_random = imgui.input_int("Random", self.gen_num_random)
            _, self.gen_num_fundamental = imgui.input_int("Fundamental", self.gen_num_fundamental)
            _, self.gen_num_mao = imgui.input_int("MAO", self.gen_num_mao)
            _, self.gen_num_momentum = imgui.input_int("Momentum", self.gen_num_momentum)
            _, self.gen_num_qlearning = imgui.input_int("QLearning", self.gen_num_qlearning)
            _, self.gen_num_dql = imgui.input_int("DQL", self.gen_num_dql)

            imgui.text("Parameters")

            _, self.gen_duration = imgui.input_int("Duration", self.gen_duration)
            _, self.gen_starting_price = imgui.input_int("Start Price", self.gen_starting_price)

            if imgui.button("Generate Simulation", 306, 30):
                output_path = str(Path(__file__).parent.parent / "simulations" / "GeneratedSimulation.xml")
                generateSimulation(self.gen_num_random, self.gen_num_fundamental, self.gen_num_mao, self.gen_num_momentum, self.gen_num_qlearning, self.gen_num_dql, duration=self.gen_duration, startingPrice=self.gen_starting_price, output=output_path)
                self._load_simulation_files()
                self.gen_status = True

            if self.gen_status:
                imgui.text("Simulation generated successfully")
            else:
                imgui.text("")

            imgui.separator()
            imgui.text("Select Simulation")

            # Simulation file selector
            changed, self.selected_simulation = imgui.combo("Preset", self.selected_simulation, self.simulation_files)

            sim_running = self.sim_manager.is_running()
            imgui.separator()
            imgui.text("Run Simulation")

            if not sim_running and imgui.button("Start Simulation", 306, 30):
                self.chart_panel.clear()
                if self.stats_panel:
                    self.stats_panel.clear()
                if self.market_panel:
                    self.market_panel.clear()
                selected_file = self.simulation_files[self.selected_simulation]
                if self.sim_manager.start_simulation(selected_file):
                    print(f"Simulation started using {selected_file}")

            if sim_running:
                if imgui.button("Stop Simulation", 306, 30):
                    self.sim_manager.stop_simulation()

            status = f"Status: {'Running' if sim_running else 'Stopped'}"
            imgui.text(status)

            imgui.separator()
            imgui.text("Save Results")
            
            imgui.end()
