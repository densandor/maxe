from threading import Thread
import subprocess
import os
import time


class SimulationManager:
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.log_file = "logs/MarketDataLog.csv"
        self.process = None
        self.running = False
        self.last_position = 0

    def start_simulation(self, xml_file):
        if self.process and self.process.poll() is None:
            print("Simulation already running")
            return False

        try:
            if os.path.exists("build/TheSimulator/TheSimulator/Debug/TheSimulator.exe"):
                sim_exe = "build/TheSimulator/TheSimulator/Debug/TheSimulator.exe"
            else:
                print("Simulator executable not found")
                return False

            # Delete old log file so we only read fresh data
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
                print(f"Cleared old log: {self.log_file}")

            # Drain any stale data from queue
            while not self.data_queue.empty():
                try:
                    self.data_queue.get_nowait()
                except:
                    break

            self.process = subprocess.Popen(
                [sim_exe, "-f", f"simulations/{xml_file}"]
            )
            self.running = True
            self.last_position = 0

            Thread(target=self._monitor_log_file, daemon=True).start()
            print(f"Simulation started, monitoring: {self.log_file}")
            return True
        except Exception as e:
            print(f"Error starting simulation: {e}")
            return False

    def stop_simulation(self):
        """Stop the running simulation"""
        if self.process:
            self.process.terminate()
            self.running = False

    def _monitor_log_file(self):
        """Tail the log file and send new data to queue"""
        while self.running:
            try:
                if not os.path.exists(self.log_file):
                    time.sleep(0.1)
                    continue

                with open(self.log_file, 'r') as f:
                    f.seek(self.last_position)
                    lines = f.readlines()
                    self.last_position = f.tell()

                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("time"):
                            try:
                                parts = line.split(',')
                                if len(parts) >= 2:
                                    time_sec = float(parts[0])
                                    price = float(parts[1])
                                    self.data_queue.put((time_sec, price))
                            except ValueError:
                                pass

                time.sleep(0.05)
            except Exception as e:
                print(f"Log monitoring error: {e}")
                time.sleep(0.1)

    def is_running(self):
        """Check if simulation process is still running"""
        if self.process is None:
            return False
        return self.process.poll() is None
