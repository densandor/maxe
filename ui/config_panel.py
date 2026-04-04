import sys
import imgui
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.generateSimulation import generateSimulation


class ConfigPanel:
    def __init__(self, sim_manager, chart_panel, stats_panel=None, market_panel=None, orderbook_panel=None):
        self.sim_manager = sim_manager
        self.chart_panel = chart_panel
        self.stats_panel = stats_panel
        self.market_panel = market_panel
        self.orderbook_panel = orderbook_panel

        self.population_files = []
        self._load_population_files()
        self.population_index = 0

        self.result_folders = []
        self._load_result_folders()
        self.folder_index = 0

        self.is_saved = False
        
        self.gen_num_random = 10
        self.gen_num_fundamental = 100
        self.gen_num_mao = 150
        self.gen_num_qlearning = 0
        self.gen_num_dql = 0
        self.gen_duration = 10000
        self.gen_starting_price = 10000
        self.is_generated = False

    def _load_population_files(self):
        simulations = Path(__file__).parent.parent / "simulations"
        self.population_files = sorted([f.name for f in simulations.glob("*.xml")])

    def _load_result_folders(self):
        results = Path(__file__).parent.parent / "results"
        self.result_folders = sorted([f.name for f in results.glob("*/") if f.is_dir()])

    def _save_results(self):
        if self.sim_manager.is_running():
            return

        logs_folder = Path(__file__).parent.parent / "logs"
        if not logs_folder.exists():
            return

        save_folder = self.result_folders[self.folder_index]
        save_path = Path(__file__).parent.parent / "results" / save_folder
        save_path.mkdir(parents=True, exist_ok=True)

        existing_runs = [int(p.name) for p in save_path.iterdir() if p.is_dir() and p.name.isdigit()]
        if existing_runs:
            next_run = max(existing_runs) + 1
        else:
            next_run = 1

        run_dir = save_path / str(next_run)
        run_dir.mkdir(parents=True, exist_ok=False)

        for item in logs_folder.iterdir():
            if item.is_file():
                shutil.copy2(item, run_dir / item.name)

    def render(self):
        imgui.set_next_window_position(0, 0, imgui.ALWAYS)
        imgui.set_next_window_size(320, 720, imgui.ALWAYS)

        if imgui.begin("Configuration"):
            imgui.text("Generate Simulation")
            imgui.text("Agents")

            _, self.gen_num_random = imgui.input_int("Random", self.gen_num_random)
            _, self.gen_num_fundamental = imgui.input_int("Fundamental", self.gen_num_fundamental)
            _, self.gen_num_mao = imgui.input_int("MAO", self.gen_num_mao)
            _, self.gen_num_qlearning = imgui.input_int("QLearning", self.gen_num_qlearning)
            _, self.gen_num_dql = imgui.input_int("DQL", self.gen_num_dql)

            imgui.text("Parameters")

            _, self.gen_duration = imgui.input_int("Duration", self.gen_duration)
            _, self.gen_starting_price = imgui.input_int("Start Price", self.gen_starting_price)

            if imgui.button("Generate Simulation", 306, 30):
                output_path = str(Path(__file__).parent.parent / "simulations" / "GeneratedSimulation.xml")
                generateSimulation(self.gen_num_random, self.gen_num_fundamental, self.gen_num_mao, self.gen_num_qlearning, self.gen_num_dql, duration=self.gen_duration, startingPrice=self.gen_starting_price, output=output_path)
                self._load_population_files()
                self.is_generated = True

            if self.is_generated:
                imgui.text("Simulation generated successfully.")
            else:
                imgui.text("Simulation not generated.")
                
            imgui.text("")
            imgui.separator()
            imgui.text("Select Simulation")

            _, self.population_index = imgui.combo("Population", self.population_index, self.population_files)

            sim_running = self.sim_manager.is_running()

            imgui.text("")
            imgui.separator()
            imgui.text("Run Simulation")

            if not sim_running and imgui.button("Start Simulation", 306, 30):
                self.chart_panel.clear()
                if self.orderbook_panel:
                    self.orderbook_panel.clear()
                if self.stats_panel:
                    self.stats_panel.clear()
                if self.market_panel:
                    self.market_panel.clear()
                selected_file = self.population_files[self.population_index]
                self.sim_manager.start_simulation(selected_file)

            if sim_running:
                if imgui.button("Stop Simulation", 306, 30):
                    self.sim_manager.stop_simulation()

            if sim_running:
                status = "Status: Running"
            else:
                status = "Status: Stopped"
            imgui.text(status)

            imgui.text("")
            imgui.separator()
            imgui.text("Save Results")

            _, self.folder_index = imgui.combo("Folder", self.folder_index, self.result_folders)

            if imgui.button("Save Results", 306, 30):
                self._save_results()
                self.is_saved = True
            
            if self.is_saved:
                imgui.text("Results saved successfully.")
            
            imgui.end()
