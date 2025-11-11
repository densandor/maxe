from xml.etree import ElementTree as ET
from xml.dom import minidom
import argparse
import subprocess
import sys
from pathlib import Path

def prettify(elem):
    rough = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="    ")

def make_simulation_xml(out_path: Path, n_agents: int,
                        base_name: str = "TRADER_RANDOM_",
                        exchange_name: str = "MARKET",
                        start: int = 0, duration: int = 3600001,
                        setup_bid_price: int = 10000, setup_ask_price: int = 10000,
                        interval: int = 1000, quantity: int = 1,
                        offset_increment: int = 1):
    root = ET.Element('Simulation', {"start": str(start), "duration": str(duration)})

    ET.SubElement(root, 'ExchangeAgent', {
        "name": exchange_name,
        "algorithm": "PriceTime"
    })

    ET.SubElement(root, 'SetupAgent', {
        "name": "SETUP_AGENT",
        "exchange": exchange_name,
        "setupTime": "0",
        "bidVolume": "1",
        "askVolume": "1",
        "bidPrice": str(setup_bid_price),
        "askPrice": str(setup_ask_price)
    })

    for i in range(n_agents):
        name = f"{base_name}{i}"
        offset = str(1 + i * offset_increment)
        ET.SubElement(root, 'RandomAgent', {
            "name": name,
            "exchange": exchange_name,
            "p_buy": "0.5",
            "quantity": str(quantity),
            "interval": str(interval),
            "offset": offset
        })

    ET.SubElement(root, 'L1LogAgent', {
        "name": "L1_LOGGER",
        "exchange": exchange_name,
        "outputFile": "L1Log.csv"
    })

    ET.SubElement(root, 'TradeLogAgent', {
        "name": "TRADE_LOGGER",
        "exchange": exchange_name,
        "outputFile": "TradeLog.csv"
    })

    xml_str = prettify(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml_str, encoding='utf-8')
    print(f"Wrote simulation XML to {out_path}")

def run_simulator(sim_exe: Path, xml_path: Path, cwd: Path = None):
    if not sim_exe.exists():
        raise FileNotFoundError(f"Simulator executable not found: {sim_exe}")
    if not xml_path.exists():
        raise FileNotFoundError(f"XML file not found: {xml_path}")

    # call the simulator with the XML path as argument
    cmd = [str(sim_exe), str(xml_path)]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, shell=False)
    if proc.returncode != 0:
        print(f"Simulator exited with return code {proc.returncode}", file=sys.stderr)
    else:
        print("Simulator finished successfully.")

def main():
    p = argparse.ArgumentParser(description="Generate simulation XML with many RandomAgents and run the simulator.")
    p.add_argument("-n", "--num", type=int, default=10, help="Number of RandomAgent instances")
    p.add_argument("-o", "--out", type=str, default="doc/generated_simulation.xml", help="Output XML path (relative to repo root)")
    p.add_argument("--exe", type=str, default="", help="Path to TheSimulator executable (if empty, only generate XML)")
    p.add_argument("--offset-inc", type=int, default=200, help="Offset increment (ms) between agents")
    p.add_argument("--interval", type=int, default=1000, help="Agent wakeup interval (ms)")
    p.add_argument("--quantity", type=int, default=1, help="Order quantity for agents")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parents[1]  # d:\Sandor\files\uni\cs310\maxe
    out_path = (repo_root / args.out).resolve()
    make_simulation_xml(out_path, n_agents=args.num,
                        offset_increment=args.offset_inc,
                        interval=args.interval,
                        quantity=args.quantity)

    if args.exe:
        sim_exe = Path(args.exe)
        # if a relative path was given, interpret it relative to repo root
        if not sim_exe.is_absolute():
            sim_exe = (repo_root / args.exe).resolve()
        run_simulator(sim_exe, out_path)

if __name__ == "__main__":
    main()