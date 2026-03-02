import argparse
import xml.etree.ElementTree as ET


def generateSimulation(numMaoSmall, numMaoLarge, numFundamental, duration=20000, startingPrice=2250):
    root = ET.Element("Simulation", start="0", duration=str(duration))

    ET.SubElement(root, "ExchangeAgent", name="MARKET", algorithm="PriceTime")
    ET.SubElement(root, "SetupAgent", name="SETUP_AGENT", exchange="MARKET",
                  setupTime="0", bidVolume="1", askVolume="1",
                  bidPrice=str(startingPrice), askPrice=str(startingPrice))
    ET.SubElement(root, "NewsAgent", name="NEWS_AGENT", offset="1",
                  newsPoissonLambda="20", standardDeviation="0.1", mean="0.0")
    ET.SubElement(root, "MarketDataAgent", name="MARKET_DATA_AGENT_SMALL", exchange="MARKET",
                  outputFile="MarketDataLog.csv", slowWindowSize="200", fastWindowSize="100")
    ET.SubElement(root, "MarketDataAgent", name="MARKET_DATA_AGENT_LARGE", exchange="MARKET",
                  outputFile="MarketDataLogLarge.csv", slowWindowSize="400", fastWindowSize="200")
    ET.SubElement(root, "L1LogAgent", name="L1_LOGGER", exchange="MARKET", outputFile="L1Log.csv")
    ET.SubElement(root, "TradeLogAgent", name="TRADE_LOGGER", exchange="MARKET", outputFile="TradeLog.csv")
    ET.SubElement(root, "PnLManagerAgent", name="PNL_AGENT", exchange="MARKET", outputFile="PortfolioHistory.csv")

    for i in range(numMaoSmall):
        ET.SubElement(root, "MAOAgent", name=f"TRADER_MAO_{i:02d}",
                      exchange="MARKET", marketDataAgent="MARKET_DATA_AGENT_SMALL")

    for i in range(numMaoSmall, numMaoSmall + numMaoLarge):
        ET.SubElement(root, "MAOAgent", name=f"TRADER_MAO_{i:02d}",
                      exchange="MARKET", marketDataAgent="MARKET_DATA_AGENT_LARGE")

    for i in range(numFundamental):
        ET.SubElement(root, "FundamentalAgent", name=f"TRADER_FUNDAMENTAL_{i:02d}", exchange="MARKET")

    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("generateSimulation")
    parser.add_argument("--maoSmall", type=int, default=750, help="Number of MAO agents using MARKET_DATA_AGENT_SMALL")
    parser.add_argument("--maoLarge", type=int, default=750, help="Number of MAO agents using MARKET_DATA_AGENT_LARGE")
    parser.add_argument("--fundamental", type=int, default=1000, help="Number of Fundamental agents")
    parser.add_argument("--duration", type=int, default=20000, help="Simulation duration")
    parser.add_argument("--startingPrice", type=int, default=2250, help="Starting bid/ask price")
    parser.add_argument("--output", default="simulations/GeneratedSimulation.xml", help="Output file path")
    args = parser.parse_args()

    xml = generateSimulation(args.maoSmall, args.maoLarge, args.fundamental,
                             duration=args.duration, startingPrice=args.startingPrice)

    with open(args.output, "w") as f:
        f.write(xml)

    totalAgents = args.maoSmall + args.maoLarge + args.fundamental
    print(f"Generated {args.output}: {args.maoSmall} MAO SMALL + {args.maoLarge} MAO LARGE + {args.fundamental} FUNDAMENTAL = {totalAgents} trading agents")
