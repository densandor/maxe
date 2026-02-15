#!/usr/bin/env python3
"""
Generate a basic simulation XML file with configurable agent counts.
"""

import argparse
import xml.dom.minidom as minidom
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring


def generate_simulation_xml(num_random, num_mao, num_fundamental, num_momentum, output_file):
    """
    Generate a simulation XML with the specified number of agents.
    
    Args:
        num_random: Number of RandomAgent agents
        num_mao: Number of MAOAgent agents
        num_fundamental: Number of FundamentalAgent agents
        num_momentum: Number of MomentumAgent agents
        output_file: Output XML file path
    """
    
    # Create root element
    simulation = Element('Simulation')
    simulation.set('start', '0')
    simulation.set('duration', '27000')
    
    # Add ExchangeAgent
    exchange = SubElement(simulation, 'ExchangeAgent')
    exchange.set('name', 'MARKET')
    exchange.set('algorithm', 'PriceTime')
    
    # Add SetupAgent
    setup = SubElement(simulation, 'SetupAgent')
    setup.set('name', 'SETUP_AGENT')
    setup.set('exchange', 'MARKET')
    setup.set('setupTime', '0')
    setup.set('bidVolume', '1')
    setup.set('askVolume', '1')
    setup.set('bidPrice', '2250')
    setup.set('askPrice', '2250')
    
    # Add NewsAgent
    news = SubElement(simulation, 'NewsAgent')
    news.set('name', 'NEWS_AGENT')
    news.set('offset', '1')
    news.set('interval', '1')
    news.set('mean', '0.0')
    news.set('standardDeviation', '0.1')
    
    # Add RandomAgents
    for i in range(num_random):
        agent = SubElement(simulation, 'RandomAgent')
        agent.set('name', f'TRADER_RANDOM_{i:02d}')
        agent.set('exchange', 'MARKET')
    
    # Add MAOAgents
    for i in range(num_mao):
        agent = SubElement(simulation, 'MAOAgent')
        agent.set('name', f'TRADER_MAO_{i:02d}')
        agent.set('exchange', 'MARKET')
    
    # Add FundamentalAgents
    for i in range(num_fundamental):
        agent = SubElement(simulation, 'FundamentalAgent')
        agent.set('name', f'TRADER_FUNDAMENTAL_{i:02d}')
        agent.set('exchange', 'MARKET')
    
    # Add MomentumAgents
    for i in range(num_momentum):
        agent = SubElement(simulation, 'MomentumAgent')
        agent.set('name', f'TRADER_MOMENTUM_{i:02d}')
        agent.set('exchange', 'MARKET')
        agent.set('offset', '1')
        agent.set('lookback', '10')
        agent.set('threshold', '0.1')
    
    # Add L1LogAgent
    l1_log = SubElement(simulation, 'L1LogAgent')
    l1_log.set('name', 'L1_LOGGER')
    l1_log.set('exchange', 'MARKET')
    l1_log.set('outputFile', 'L1Log.csv')
    
    # Add TradeLogAgent
    trade_log = SubElement(simulation, 'TradeLogAgent')
    trade_log.set('name', 'TRADE_LOGGER')
    trade_log.set('exchange', 'MARKET')
    trade_log.set('outputFile', 'TradeLog.csv')
    
    # Add PnLManagerAgent
    pnl = SubElement(simulation, 'PnLManagerAgent')
    pnl.set('name', 'PNL_AGENT')
    pnl.set('exchange', 'MARKET')
    
    # Pretty print the XML
    xml_bytes = tostring(simulation, encoding='utf-8')
    xml_str = minidom.parseString(xml_bytes).toprettyxml(indent='    ')
    # Remove the XML declaration and extra blank lines
    xml_str = '\n'.join([line for line in xml_str.split('\n')[1:] if line.strip()])
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write('<?xml version="1.0" ?>\n')
        f.write(xml_str)
    
    print(f"Generated simulation XML: {output_file}")
    print(f"  - {num_random} RandomAgents")
    print(f"  - {num_mao} MAOAgents")
    print(f"  - {num_fundamental} FundamentalAgents")
    print(f"  - {num_momentum} MomentumAgents")
    print(f"  - 1 NewsAgent")
    print(f"  - 1 L1LogAgent")
    print(f"  - 1 TradeLogAgent")
    print(f"  - 1 PnLManagerAgent")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate a simulation XML file with configurable agent counts'
    )
    parser.add_argument('--random', type=int, default=20, help='Number of RandomAgents (default: 20)')
    parser.add_argument('--mao', type=int, default=0, help='Number of MAOAgents (default: 0)')
    parser.add_argument('--fundamental', type=int, default=0, help='Number of FundamentalAgents (default: 0)')
    parser.add_argument('--momentum', type=int, default=0, help='Number of MomentumAgents (default: 0)')
    parser.add_argument('--output', type=str, default='simulations/GeneratedSimulation.xml', help='Output file path (default: simulations/GeneratedSimulation.xml)')
    
    args = parser.parse_args()
    
    generate_simulation_xml(
        num_random=args.random,
        num_mao=args.mao,
        num_fundamental=args.fundamental,
        num_momentum=args.momentum,
        output_file=args.output
    )
