# Agent-Based Market Simulator

An interactive agent-based trading simulator with real-time visualization and performance analysis used to analyse the impact of order-matching algorithms and agent populations on adaptive strategies.

The project was developed using the [MAXE framework](https://github.com/maxe-team/maxe).

## Installation

### Software Requirements

Development was done on Windows with the following software versions:

- CMake 4.2.0
- Python 3.10.11
- Microsoft Visual Studio Community 2026 18.4.3 (with the 'Desktop Development with C++' toolset)

However, these are not hard requirements. For more information about the software requirements on different platforms, take a look at the following requirements, which were taken directly from the [README of the MAXE repository](https://github.com/maxe-team/maxe/blob/master/README.md):

On Windows you need:

- `cmake` 3.15+
- MSVC 15.7+
- `python` on your system (tick the Python C headers options in the installation if not automatically included in your python version)

On Linux (tested with Ubuntu) you need:

- `cmake` 3.15+
- GCC 9.0+ (similarly slave `g++` of the same version, or manually add `filesystem` dependency, i.e. `#include <experimental/filesystem>` and compile with `-lstdc++fs`), _or_ LLVM Clang 9.0+ (or LLVM 7.0+ and LLVM 8.0+ with the aforementioned experimental and `stdc++fs` fix)
- `python` on your system (preferably with `python-all` or at least `distutils`)
- `python-dev` for Python C headers
- Remember that if you're using Python 3, you will need the `python3` equivalents of everything (i.e. `python3-all`, `python3-dev`).

On MacOS you need:

- MacOS 10.15 Catalina or newer (for `std::filesystem::path` support)
- Xcode 11.0+ (for `#include <filesystem>` to work, otherwise see the note for LLVM 9.0 above)
- LLVM Clang 9.0+

### Package Requirements

Python package requirements can be found in `requirements.txt`.

The project was developed using PyTorch with CUDA. However, PyTorch with CUDA is not strictly necessary, therefore only the base PyTorch is listed in `requirements.txt`.

### Build

To build the simulator:

1. Clone the repository with `--recurse-submodules` the repository into a directory called `thesimulator`.

   Note: If you have cloned without `--recurse-submodules`, do `git submodule init && git submodule update`.

2. Run the following:

```
cd thesimulator

mkdir build
cd build
cmake ../
cmake --build .
```

3. Install the Python packages in `requirements.txt` using `pip install -r requirements.txt` or your preferred Python package manager.

4. Done! For details on how to use the simulator, take a look at [Usage](#usage)!

## Usage

Once you have built the project:

1. Run the UI using `python .\ui\StartUI.py` from the root.

2. In the Configuration panel, select a population preset or generate a new one.

   Simulation files can be found in the `simulations` folder.

   To fine-tune the simulation parameters, you can edit the XML file. For more details, read the [Simulation Files](#simulation-files) section.

3. Run the simulation and wait for it to finish.

4. Save the results to the chosen folder (found in the `results` folder).

## Simulation Files

Simulation files are XML-based configurations that define the structure of a market simulation, including the exchange properties, market participants, and data logging agents. Below is a detailed breakdown of the format and available agent options.

### General Structure

A simulation file follows this basic XML structure (but the order of elements do not matter):

```xml
<?xml version='1.0' encoding='utf-8'?>
<Simulation start="0" duration="10000">
    <!-- Exchange configuration -->
    <!-- Setup agents -->
    <!-- News/data agents -->
    <!-- Trading agents -->
</Simulation>
```

**Root Element Attributes:**

- `start`: The simulation start timestamp (typically 0)
- `duration`: Total simulation duration in milliseconds

### Core Components

#### 1. **ExchangeAgent**

Defines the market exchange and its matching algorithm.

```xml
<ExchangeAgent name="MARKET" algorithm="PureProRata" />
```

**Attributes:**

- `name`: Identifier for the exchange (used by other agents to reference it)
- `algorithm`: Order matching algorithm to use
  - `PureProRata`: Pro-rata allocation at each price level
  - `PriorityProRata`: Pro-rata with priority given to orders that improved the best price

#### 2. **SetupAgent**

Initializes the market with a single trade at a specific price.

```xml
<SetupAgent name="SETUP_AGENT" exchange="MARKET" setupTime="0" bidVolume="1"
            askVolume="1" bidPrice="10000" askPrice="10000" />
```

**Attributes:**

- `name`: Agent identifier
- `exchange`: Which exchange to initialize
- `setupTime`: Timestamp to place seed orders
- `bidVolume`: Volume to post at bid price
- `askVolume`: Volume to post at ask price
- `bidPrice`: The bid price (in cents)
- `askPrice`: The ask price (in cents)

#### 3. **NewsAgent**

Simulates news arrival that impacts the fundamental price estimate agents use.

```xml
<NewsAgent name="NEWS_AGENT" offset="1" newsPoissonLambda="20"
           standardDeviation="5" mean="0.0" />
```

**Attributes:**

- `name`: Agent identifier
- `offset`: Initial delay before first news event
- `newsPoissonLambda`: Poisson parameter for news inter-arrival times
- `standardDeviation`: Std dev of news impact distribution
- `mean`: Mean of news impact distribution

#### 4. **Data and Logging Agents**

Various agents that collect and log market data without actively trading.

**MarketDataAgent** - Computes moving average signals

```xml
<MarketDataAgent name="MARKET_DATA_AGENT_SMALL" exchange="MARKET"
                 outputFile="MarketDataLogSmall.csv" slowWindowSize="200"
                 fastWindowSize="100" />
```

- `outputFile`: CSV file to write data to
- `slowWindowSize`: Window size for slow moving average
- `fastWindowSize`: Window size for fast moving average

**L1LogAgent** - Logs order book level 1 (best bid/ask)

```xml
<L1LogAgent name="L1_LOGGER" exchange="MARKET" outputFile="L1Log.csv" />
```

**TradeLogAgent** - Logs all trades

```xml
<TradeLogAgent name="TRADE_LOGGER" exchange="MARKET" outputFile="TradeLog.csv" />
```

**PortfolioAgent** - Logs agent portfolio values

```xml
<PortfolioAgent name="PORTFOLIO_AGENT" exchange="MARKET" outputFile="PortfolioLog.csv" />
```

### Trading Agent Types

#### **RandomAgent**

Places random orders at random prices near the current market price.

```xml
<RandomAgent name="TRADER_RANDOM_00" exchange="MARKET" />
```

**Common Parameters:**

- `name`: Agent identifier
- `exchange`: Which exchange to trade on
- `offset`: (optional, default=1) Initial delay before first trade decision
- `interval`: (optional, default=1) Time between trade decisions
- `pTrade`: (optional, default=random [0.2, 0.4]) Probability of trading at each interval
- `pMarketOrder`: (optional, default=1) Probability of submitting a market vs limit order
- `volume`: (optional, default=1) Order size in shares

**Strategy:** Randomly decides buy/sell direction, submits orders near last trade price.

#### **FundamentalAgent**

Trades based on perceived mispricing relative to a fundamental value estimate that updates with news.

```xml
<FundamentalAgent name="TRADER_FUNDAMENTAL_00" exchange="MARKET" />
```

**Specific Parameters:**

- `newsAgent`: (optional, default="NEWS_AGENT") Which news agent to subscribe to
- `fundamentalPrice`: (optional, default=random [90, 110]) Initial estimated fundamental value
- `priceUpdateSigma`: (optional, default=1) Std dev for random fundamental price updates
- `marketOrderThreshold`: (optional, default=random [0.005, 0.25]) Min mispricing (in %) to submit market orders
- `opinionThreshold`: (optional, default=random [0.01, 0.1]) Min mispricing (in %) to trade at all
- `limitOrderLambda`: (optional, default=5) Lambda for exponential distribution of limit order prices

**Strategy:** Submits market orders when mispricing exceeds `marketOrderThreshold`, limit orders when mispricing exceeds `opinionThreshold`, updates fundamental price estimate based on news.

#### **QLearningAgent**

Uses Q-learning (tabular reinforcement learning) to learn trading policies based on position and price trend.

```xml
<QLearningAgent name="TRADER_QL_00" exchange="MARKET" pnlAgent="PNL_AGENT" />
```

**Specific Parameters:**

- `pnlAgent`: (optional, default="PNL_AGENT") Agent to query for current PnL and position
- `alpha`: (optional, default=0.05) Q-learning rate (how quickly to update Q-values)
- `gamma`: (optional, default=0.99) Discount factor (weight of future rewards)
- `epsilon`: (optional, default=1) Initial exploration rate
- `minEpsilon`: (optional, default=0.01) Minimum exploration rate after decay
- `epsilonDecay`: (optional, default=0.995) Exploration rate decay per episode

**State Space:** 9 discrete states = Position (-1, 0, +1) × Price Trend (-1, 0, +1)

**Action Space:** 3 actions = Go Short (-1), Go Flat (0), Go Long (+1)

**Strategy:** Learns Q-values for state-action pairs to maximize cumulative PnL. Follows epsilon-greedy exploration.

#### **Deep Q-Learning Agent (DQLAgent)**

Uses a neural network to approximate Q-values for continuous state spaces and advanced trading decisions.

```xml
<DQLAgent name="TRADER_DQL_00" exchange="MARKET" pnlAgent="PNL" />
```

**Specific Parameters:**

- `pnlAgent`: (optional, default="PNL") Agent to query for PnL
- `alpha`: (optional, default=0.1) Learning rate for network optimizer
- `gamma`: (optional, default=0.99) Discount factor
- `epsilon`: (optional, default=1.0) Initial exploration rate
- `minEpsilon`: (optional, default=0.1) Minimum exploration rate
- `epsilonDecay`: (optional, default=0.995) Exploration rate decay
- `batchSize`: (optional, default=50) Batch size for network training
- `memoryCapacity`: (optional, default=10000) Replay memory buffer size
- `targetNetworkUpdateFrequency`: (optional, default=100) Steps between target network updates

**State Features:** 4-dimensional = Position + Normalized Price + Price Trend + Volatility

**Action Space:** 3 actions = Sell, Hold, Buy

**Strategy:** Uses two neural networks (Q-network and target network) with experience replay to learn optimal trading policy. More sophisticated than Q-Learning, suitable for continuous state spaces.

#### **Moving Average Oscillator Agent (MAOAgent)**

Trades based on moving average crossover signals (technical analysis / momentum strategy).

```xml
<MAOAgent name="TRADER_MAO_00" exchange="MARKET" pnlAgent="PNL_AGENT"
          marketDataAgent="MARKET_DATA_AGENT" />
```

**Specific Parameters:**

- `pnlAgent`: (optional, default="PNL_AGENT") Agent for querying position/inventory
- `marketDataAgent`: (optional, default="MARKET_DATA_AGENT") Agent providing moving average signals
- `profitFactor`: (optional, default=random [0.01, 0.2]) Take-profit target as % above entry price
- `waitTime`: (optional, default=random [0, 50]) Milliseconds to wait before acting on moving average signals

**Strategy:** Subscribes to moving average crossover signals from a market data agent, trades with position sizing based on current inventory, exits with profit targets.

### Configuration Example

Below is a minimal complete simulation:

```xml
<?xml version='1.0' encoding='utf-8'?>
<Simulation start="0" duration="10000">
    <ExchangeAgent name="MARKET" algorithm="PureProRata" />
    <SetupAgent name="SETUP_AGENT" exchange="MARKET" setupTime="0"
                bidVolume="10" askVolume="10" bidPrice="10000" askPrice="10100" />
    <NewsAgent name="NEWS_AGENT" offset="1" newsPoissonLambda="20"
               standardDeviation="5" mean="0.0" />
    <MarketDataAgent name="MARKET_DATA" exchange="MARKET"
                     outputFile="MarketData.csv" slowWindowSize="200" fastWindowSize="100" />
    <L1LogAgent name="L1_LOGGER" exchange="MARKET" outputFile="L1Log.csv" />
    <TradeLogAgent name="TRADE_LOGGER" exchange="MARKET" outputFile="TradeLog.csv" />
    <PortfolioAgent name="PORTFOLIO_AGENT" exchange="MARKET" outputFile="PortfolioLog.csv" />

    <!-- 5 random traders -->
    <RandomAgent name="TRADER_RANDOM_00" exchange="MARKET" />
    <RandomAgent name="TRADER_RANDOM_01" exchange="MARKET" />
    <RandomAgent name="TRADER_RANDOM_02" exchange="MARKET" />
    <RandomAgent name="TRADER_RANDOM_03" exchange="MARKET" />
    <RandomAgent name="TRADER_RANDOM_04" exchange="MARKET" />

    <!-- 10 fundamental traders -->
    <FundamentalAgent name="TRADER_FUNDAMENTAL_00" exchange="MARKET" />
    <FundamentalAgent name="TRADER_FUNDAMENTAL_01" exchange="MARKET" />
    <!-- ... more fundamental agents ... -->

    <!-- 3 RL-based traders -->
    <QLearningAgent name="TRADER_QL_00" exchange="MARKET" pnlAgent="PNL_AGENT" />
    <DQLAgent name="TRADER_DQL_00" exchange="MARKET" pnlAgent="PNL" />
    <MAOAgent name="TRADER_MAO_00" exchange="MARKET" pnlAgent="PNL_AGENT"
              marketDataAgent="MARKET_DATA" />
</Simulation>
```
