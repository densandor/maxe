from threading import Thread
import subprocess
import os
import time


class SimulationManager:
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.process = None
        self.running = False

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

            # Drain any stale data from queue
            while not self.data_queue.empty():
                try:
                    self.data_queue.get_nowait()
                except:
                    break

            self.process = subprocess.Popen(
                [sim_exe, "-f", f"simulations/{xml_file}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self.running = True

            Thread(target=self._monitor_stdout, daemon=True).start()
            print("Simulation started, monitoring stdout")
            return True
        except Exception as e:
            print(f"Error starting simulation: {e}")
            return False

    def stop_simulation(self):
        """Stop the running simulation"""
        if self.process:
            self.process.terminate()
            self.running = False

    def _monitor_stdout(self):
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
                if not line.startswith("UI_TICK,"):
                    continue

                parts = line.split(',')
                if len(parts) != 3:
                    continue

                try:
                    time_sec = float(parts[1])
                    price = float(parts[2])
                    self.data_queue.put((time_sec, price))
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
