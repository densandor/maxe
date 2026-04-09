import imgui
import shutil
from pathlib import Path

from scripts.generateSimulation import generateSimulation


class ConfigPanel:
    def __init__(self, simManager, chartPanel, statsPanel=None, marketPanel=None, orderbookPanel=None):
        self.simManager = simManager
        self.chartPanel = chartPanel
        self.statsPanel = statsPanel
        self.marketPanel = marketPanel
        self.orderbookPanel = orderbookPanel

        self.populationFiles = []
        self._loadPopulationFiles()
        self.populationIndex = 0

        self.resultFolders = []
        self._loadResultFolders()
        self.folderIndex = 0

        self.isSaved = False
        
        self.genNumRandom = 10
        self.genNumFundamental = 100
        self.genNumMao = 150
        self.genNumQLearning = 0
        self.genNumDQL = 0
        self.genDuration = 10000
        self.genStartingPrice = 10000
        self.genAlgorithm = 1  # 0=PureProRata, 1=PriceTime, 2=PriorityProRata, 3=TimeProRata
        self.algorithmOptions = ["PureProRata", "PriceTime", "PriorityProRata", "TimeProRata"]
        self.isGenerated = False

    def _loadPopulationFiles(self):
        simulations = Path(__file__).parent.parent / "simulations"
        self.populationFiles = sorted([f.name for f in simulations.glob("*.xml")])

    def _loadResultFolders(self):
        results = Path(__file__).parent.parent / "results"
        results.mkdir(parents=True, exist_ok=True)
        self.resultFolders = sorted([f.name for f in results.glob("*/") if f.is_dir()])

    def _saveResults(self):
        if self.simManager.is_running():
            return

        logsFolder = Path(__file__).parent.parent / "logs"
        if not logsFolder.exists():
            return

        resultsRoot = Path(__file__).parent.parent / "results"
        resultsRoot.mkdir(parents=True, exist_ok=True)

        if not self.resultFolders:
            defaultFolder = resultsRoot / "population1"
            defaultFolder.mkdir(parents=True, exist_ok=True)
            self._loadResultFolders()

        saveFolder = self.resultFolders[self.folderIndex]
        savePath = resultsRoot / saveFolder
        savePath.mkdir(parents=True, exist_ok=True)

        existingRuns = [int(p.name) for p in savePath.iterdir() if p.is_dir() and p.name.isdigit()]
        if existingRuns:
            nextRun = max(existingRuns) + 1
        else:
            nextRun = 1

        runDir = savePath / str(nextRun)
        runDir.mkdir(parents=True, exist_ok=False)

        for item in logsFolder.iterdir():
            if item.is_file():
                shutil.copy2(item, runDir / item.name)

    def render(self):
        imgui.set_next_window_position(0, 0, imgui.ONCE)
        imgui.set_next_window_size(320, 720, imgui.ONCE)

        if imgui.begin("Configuration"):
            imgui.text("Generate Simulation")
            imgui.text("Agents")

            _, self.genNumRandom = imgui.input_int("Random", self.genNumRandom)
            _, self.genNumFundamental = imgui.input_int("Fundamental", self.genNumFundamental)
            _, self.genNumMao = imgui.input_int("MAO", self.genNumMao)
            _, self.genNumQLearning = imgui.input_int("QLearning", self.genNumQLearning)
            _, self.genNumDQL = imgui.input_int("DQL", self.genNumDQL)

            imgui.text("Parameters")

            _, self.genDuration = imgui.input_int("Duration", self.genDuration)
            _, self.genStartingPrice = imgui.input_int("Start Price", self.genStartingPrice)
            _, self.genAlgorithm = imgui.combo("Algorithm", self.genAlgorithm, self.algorithmOptions)

            if imgui.button("Generate Simulation", 306, 30):
                outputPath = str(Path(__file__).parent.parent / "simulations" / "GeneratedSimulation.xml")
                selectedAlgorithm = self.algorithmOptions[self.genAlgorithm]
                generateSimulation(self.genNumRandom, self.genNumFundamental, self.genNumMao, self.genNumQLearning, self.genNumDQL, duration=self.genDuration, startingPrice=self.genStartingPrice, algorithm=selectedAlgorithm, output=outputPath)
                self._loadPopulationFiles()
                self.isGenerated = True

            if self.isGenerated:
                imgui.text("Simulation generated successfully.")
            else:
                imgui.text("Simulation not generated.")
                
            imgui.text("")
            imgui.separator()
            imgui.text("Select Simulation")

            _, self.populationIndex = imgui.combo("Population", self.populationIndex, self.populationFiles)

            simRunning = self.simManager.is_running()

            imgui.text("")
            imgui.separator()
            imgui.text("Run Simulation")

            if not simRunning and imgui.button("Start Simulation", 306, 30):
                self.chartPanel.clear()
                if self.orderbookPanel:
                    self.orderbookPanel.clear()
                if self.statsPanel:
                    self.statsPanel.clear()
                if self.marketPanel:
                    self.marketPanel.clear()
                self.isSaved = False
                selectedFile = self.populationFiles[self.populationIndex]
                self.simManager.startSimulation(selectedFile)

            if simRunning:
                if imgui.button("Stop Simulation", 306, 30):
                    self.simManager.stopSimulation()

            if simRunning:
                status = "Status: Running"
            else:
                status = "Status: Stopped"
            imgui.text(status)

            imgui.text("")
            imgui.separator()
            imgui.text("Save Results")

            _, self.folderIndex = imgui.combo("Folder", self.folderIndex, self.resultFolders)

            if imgui.button("Save Results", 306, 30):
                self._saveResults()
                self.isSaved = True
            
            if self.isSaved:
                imgui.text("Results saved successfully.")
            
            imgui.end()
