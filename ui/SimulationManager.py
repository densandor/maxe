from threading import Thread
import subprocess
import os
import time
import queue


class SimulationManager:
    def __init__(self, dataQueue, orderBookQueue=None):
        self.dataQueue = dataQueue
        self.orderBookQueue = orderBookQueue
        self.process = None
        self.running = False
        self.latestTradePrice = None

    def _putLatest(self, targetQueue, item):
        """Push item to bounded queue, dropping oldest item if full."""
        if targetQueue is None:
            return
        try:
            targetQueue.put_nowait(item)
        except queue.Full:
            try:
                targetQueue.get_nowait()
            except queue.Empty:
                pass
            try:
                targetQueue.put_nowait(item)
            except queue.Full:
                pass

    def startSimulation(self, xmlFile):
        if self.process and self.process.poll() is None:
            print("Simulation already running")
            return False

        try:
            if os.path.exists("build/TheSimulator/TheSimulator/Debug/TheSimulator.exe"):
                simExe = "build/TheSimulator/TheSimulator/Debug/TheSimulator.exe"
            else:
                print("Simulator executable not found")
                return False

            # Drain any stale data from queue
            while not self.dataQueue.empty():
                try:
                    self.dataQueue.get_nowait()
                except:
                    break
            if self.orderBookQueue is not None:
                while not self.orderBookQueue.empty():
                    try:
                        self.orderBookQueue.get_nowait()
                    except:
                        break

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
        """Stop the running simulation"""
        if self.process:
            self.process.terminate()
            self.running = False

    def _monitorStdout(self):
        """Read simulator stdout stream and send live ticks to queue."""
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
                        self._putLatest(self.dataQueue, (timeSec, price))
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
                            self._putLatest(self.orderBookQueue, (timeSec, side, price, qty))
                    except ValueError:
                        pass
                    continue

                # Reset marker: R,time
                if recordType == "R" and len(parts) >= 2:
                    try:
                        timeSec = float(parts[1])
                        self._putLatest(self.orderBookQueue, ("R", timeSec))
                    except ValueError:
                        pass
            except Exception as e:
                print(f"Stream monitoring error: {e}")
                time.sleep(0.1)

    def is_running(self):
        """Check if simulation process is still running"""
        if self.process is None:
            return False
        return self.process.poll() is None
