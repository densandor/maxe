from threading import Thread
import subprocess
import os
import time
from collections import deque


class SimulationManager:
    def __init__(self, dataQueue=None, orderBookQueue=None):
        self.dataQueue = dataQueue if dataQueue is not None else deque(maxlen=10000)
        self.orderBookQueue = orderBookQueue if orderBookQueue is not None else deque(maxlen=10000)
        self.process = None
        self.running = False
        self.latestTradePrice = None

    def startSimulation(self, xmlFile):
        try:
            if os.path.exists("build/TheSimulator/TheSimulator/Debug/TheSimulator.exe"):
                simExe = "build/TheSimulator/TheSimulator/Debug/TheSimulator.exe"
            elif os.path.exists("build/TheSimulator/TheSimulator/Release/TheSimulator.exe"):
                simExe = "build/TheSimulator/TheSimulator/Release/TheSimulator.exe"
            else:
                print("Simulator executable not found")
                return False

            # Drain any stale data from deque
            self.dataQueue.clear()
            self.orderBookQueue.clear()

            self.process = subprocess.Popen(
                [simExe, "-f", f"simulations/{xmlFile}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self.running = True

            Thread(target=self._monitorStdout, daemon=True).start()
            print("Simulation started, monitoring stdout.")
            return True
        except Exception as e:
            print(f"Error starting simulation: {e}")
            return False

    def stopSimulation(self):
        if self.process:
            self.process.terminate()
            self.running = False

    def _monitorStdout(self):
        if not self.process or not self.process.stdout:
            return

        while self.running:
            try:
                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue

                line = line.strip()
                parts = line.split(',')
                if not parts:
                    continue

                recordType = parts[0]

                # Tick update: T,time,last_price
                if recordType == "T" and len(parts) >= 3:
                    try:
                        timeSec = float(parts[1])
                        price = float(parts[2])
                        self.latestTradePrice = price
                        self.dataQueue.append((timeSec, price))
                    except ValueError:
                        pass
                    continue

                # Book level update: B,time,side,price,qty
                if recordType == "B" and len(parts) >= 5:
                    try:
                        timeSec = float(parts[1])
                        side = parts[2].strip().upper()
                        if side:
                            side = side[0]
                        price = float(parts[3])
                        qty = float(parts[4])
                        if side in ("B", "A"):
                            self.orderBookQueue.append((timeSec, side, price, qty))
                    except ValueError:
                        pass
                    continue

                # Reset marker: R,time
                if recordType == "R" and len(parts) >= 2:
                    try:
                        timeSec = float(parts[1])
                        self.orderBookQueue.append(("R", timeSec))
                    except ValueError:
                        pass
            except Exception as e:
                print(f"Stream monitoring error: {e}")
                time.sleep(0.1)

    def is_running(self):
        if self.process is None:
            return False
        return self.process.poll() is None
