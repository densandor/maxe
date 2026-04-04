from threading import Thread
import subprocess
import os
import time
import queue


class SimulationManager:
    def __init__(self, data_queue, order_book_queue=None):
        self.data_queue = data_queue
        self.order_book_queue = order_book_queue
        self.process = None
        self.running = False
        self.latest_trade_price = None

    def _put_latest(self, target_queue, item):
        """Push item to bounded queue, dropping oldest item if full."""
        if target_queue is None:
            return
        try:
            target_queue.put_nowait(item)
        except queue.Full:
            try:
                target_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                target_queue.put_nowait(item)
            except queue.Full:
                pass

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
            if self.order_book_queue is not None:
                while not self.order_book_queue.empty():
                    try:
                        self.order_book_queue.get_nowait()
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
            print("Simulation started, monitoring stdout.")
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
                parts = line.split(',')
                if not parts:
                    continue

                record_type = parts[0]

                # Tick update: T,time,last_price
                if record_type == "T" and len(parts) >= 3:
                    try:
                        time_sec = float(parts[1])
                        price = float(parts[2])
                        self.latest_trade_price = price
                        self._put_latest(self.data_queue, (time_sec, price))
                    except ValueError:
                        pass
                    continue

                # Book level update: B,time,side,price,qty
                if record_type == "B" and len(parts) >= 5:
                    try:
                        time_sec = float(parts[1])
                        side = parts[2].strip().upper()
                        if side:
                            side = side[0]
                        price = float(parts[3])
                        qty = float(parts[4])
                        if side in ("B", "A"):
                            self._put_latest(self.order_book_queue, (time_sec, side, price, qty))
                    except ValueError:
                        pass
                    continue

                # Reset marker: R,time
                if record_type == "R" and len(parts) >= 2:
                    try:
                        time_sec = float(parts[1])
                        self._put_latest(self.order_book_queue, ("R", time_sec))
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
