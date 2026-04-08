import argparse
import xml.etree.ElementTree as ET


def generateSimulation(numRandom, numFundamental, numMao, numQLearning, numDQL, duration=10000, startingPrice=10000, algorithm="PriceTime", output="simulations/GeneratedSimulation.xml"):
    root = ET.Element("Simulation", start="0", duration=str(duration))

    ET.SubElement(root, "ExchangeAgent", name="MARKET", algorithm=algorithm)
    ET.SubElement(root, "SetupAgent", name="SETUP_AGENT", exchange="MARKET", setupTime="0", bidVolume="1", askVolume="1", bidPrice=str(startingPrice), askPrice=str(startingPrice))
    ET.SubElement(root, "NewsAgent", name="NEWS_AGENT", offset="1", newsPoissonLambda="20", standardDeviation="5", mean="0.0")
    ET.SubElement(root, "MarketDataAgent", name="MARKET_DATA_AGENT_SMALL", exchange="MARKET", outputFile="MarketDataLogSmall.csv", slowWindowSize="200", fastWindowSize="100")
    ET.SubElement(root, "MarketDataAgent", name="MARKET_DATA_AGENT_LARGE", exchange="MARKET", outputFile="MarketDataLogLarge.csv", slowWindowSize="400", fastWindowSize="200")
    ET.SubElement(root, "L1LogAgent", name="L1_LOGGER", exchange="MARKET", outputFile="L1Log.csv")
    ET.SubElement(root, "OrderBookLogAgent", name="ORDER_BOOK_LOGGER", exchange="MARKET", outputFile="OrderBookLog.csv")
    ET.SubElement(root, "TradeLogAgent", name="TRADE_LOGGER", exchange="MARKET", outputFile="TradeLog.csv")
    ET.SubElement(root, "PortfolioAgent", name="PORTFOLIO_AGENT", exchange="MARKET", outputFile="PortfolioLog.csv")
 
    for i in range(numRandom):
        ET.SubElement(root, "RandomAgent", name=f"TRADER_RANDOM_{i:02d}", exchange="MARKET")

    for i in range(numFundamental):
        ET.SubElement(root, "FundamentalAgent", name=f"TRADER_FUNDAMENTAL_{i:02d}", exchange="MARKET")

    half = numMao // 2
    for i in range(half):
        ET.SubElement(root, "MAOAgent", name=f"TRADER_MAO_SMALL_{i:02d}", exchange="MARKET", marketDataAgent="MARKET_DATA_AGENT_SMALL")

    for i in range(half):
        ET.SubElement(root, "MAOAgent", name=f"TRADER_MAO_LARGE_{i:02d}", exchange="MARKET", marketDataAgent="MARKET_DATA_AGENT_LARGE")

    for i in range(numQLearning):
        ET.SubElement(root, "QLearningAgent", name=f"TRADER_QL_{i:02d}", exchange="MARKET")

    for i in range(numDQL):
        ET.SubElement(root, "DQLAgent", name=f"TRADER_DQL_{i:02d}", exchange="MARKET")
   
    ET.indent(root, space="    ")

    xml = ET.tostring(root, encoding="unicode", xml_declaration=True)

    with open(output, "w") as f:
        f.write(xml)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("generateSimulation")
    parser.add_argument("--random", type=int, default=10, help="Number of Random agents")
    parser.add_argument("--fundamental", type=int, default=100, help="Number of Fundamental agents")
    parser.add_argument("--mao", type=int, default=150, help="Number of MAO agents")
    parser.add_argument("--qlearning", type=int, default=0, help="Number of QLearning agents")
    parser.add_argument("--dql", type=int, default=0, help="Number of DQL agents")
    parser.add_argument("--duration", type=int, default=10000, help="Simulation duration")
    parser.add_argument("--startingPrice", type=int, default=10000, help="Starting bid/ask price (in cents)")
    parser.add_argument("--algorithm", type=str, default="PriceTime", choices=["PureProRata", "PriceTime", "PriorityProRata", "TimeProRata"], help="Order matching algorithm")
    parser.add_argument("--output", default="simulations/GeneratedSimulation.xml", help="Output file path")
    args = parser.parse_args()

    generateSimulation(args.random, args.fundamental, args.mao, args.qlearning, args.dql, duration=args.duration, startingPrice=args.startingPrice, algorithm=args.algorithm, output=args.output)

    