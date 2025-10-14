# MT5 Algorithmic Trading Bot

This project is a containerized, event-driven algorithmic trading bot designed to connect to the MetaTrader 5 (MT5) terminal. It features a modular architecture that supports multiple trading strategies, real-time data processing, backtesting, comprehensive risk management, and a resilient, redundant infrastructure.

## Architecture Overview

The system utilizes a microservices-style architecture, containerized with Docker, to ensure separation of concerns and scalability. The core components communicate via a RabbitMQ message broker.

### Data Flow

1.  **MT5 Terminal**: The process starts with the MetaTrader 5 Desktop Terminal, which must be running on the host machine.
2.  **MT5 Bridge & Watchdog**: The `mt5_watchdog.py` script is run on the host. It starts and supervises the `mt5_bridge.py` script. The bridge connects to the MT5 Terminal, subscribes to tick data for specified symbols, and publishes each tick as a message to the `realtime_data` queue in RabbitMQ. It also sends a periodic heartbeat to the `mt5_bridge_heartbeat` queue.
3.  **RabbitMQ**: Acts as the central message bus, decoupling the data producer (bridge) from the data consumer (bot).
4.  **Bot Consumer**: The `Consumer` class within the `bot` container listens for messages on the `realtime_data` queue. Upon receiving a tick, it passes the data to the currently loaded trading strategy.
5.  **Strategy**: The strategy class analyzes the tick data (and potentially other data like sentiment scores or secondary symbols) and generates a signal: `BUY`, `SELL`, or `HOLD`.
6.  **Order Manager**: If a `BUY` or `SELL` signal is generated, the `Consumer` instructs the `OrderManager` to place an order. The `OrderManager` is responsible for all aspects of trade execution, including position sizing and risk checks.
7.  **Databases**:
    - **InfluxDB**: Used for storing all time-series data, such as market ticks and performance metrics.
    - **PostgreSQL**: Used for storing structured data like trade records, order history, and strategy configurations.

## Core Features

This bot is equipped with a wide range of professional-grade features:

### Technical Foundation

- **Programming Language**: Developed primarily in Python.
- **Containerized Environment**: All core services (bot logic, databases, message queue) are containerized with Docker for consistent and reproducible deployments.
- **Modular Architecture**: The code is separated into distinct modules for data management, strategies, execution, analytics, and more, allowing for easy extension.
- **Database Integration**: Utilizes InfluxDB for high-performance time-series data storage (market ticks, metrics) and PostgreSQL for structured data (trade records, configurations).
- **User Interface**: Features a Command Line Interface (CLI) for direct interaction and a basic Flask web interface for monitoring.
- **Secure Configuration**: All sensitive credentials (broker details, API keys) are encrypted and managed via environment variables.

### Redundancy & Reliability

- **Comprehensive Logging**: A robust logging system ensures all critical operations, errors, and warnings are recorded for monitoring and debugging.
- **Resilient Connections**: All connections to external services (PostgreSQL, InfluxDB, RabbitMQ) are wrapped in a custom retry decorator (`@retry_with_backoff`) that handles connection failures with exponential backoff and jitter, preventing crashes due to transient network issues.
- **Persistent Consumer**: The core `Consumer` that processes market data is built within a resilient loop. If the connection to the RabbitMQ broker is lost, it will automatically and indefinitely attempt to reconnect without crashing the bot.
- **Data Feed Watchdog**: A standalone `mt5_watchdog.py` script runs on the host machine to monitor the critical `mt5_bridge.py` process. It listens for a heartbeat and checks the process status, automatically restarting the bridge if it fails.

### Market Analysis & Context

- **Live MT5 Integration**: Connects directly to a live MT5 terminal for real-time tick data via `mt5_bridge.py` and for downloading historical data for backtesting via `historical_data_importer.py`.
- **Advanced News & Sentiment Analysis**: Integrates with Alpha Vantage API to fetch financial news and provides pre-calculated sentiment scores. Strategies can leverage this sentiment for more informed decisions.
- **Economic Calendar Awareness**: Fetches high-impact economic events and can pause trading during configurable quiet periods around these events to mitigate volatility risks.
- **Intermarket Analysis**: Utilizes a `MarketContextAnalyzer` to calculate correlation matrices and indices between symbols, providing deeper insights into market relationships. Strategies can dynamically adapt based on these intermarket correlations.
- **Enhanced Signal Detection**: Incorporates multi-factor signal strength scoring, market regime detection (Trending, Ranging, Volatile), and seasonality-aware signal generation for more nuanced trading decisions.
- **Asset-Specific Customization**: Supports customized instrument profiles and liquidity-based adjustments to position sizing, tailoring trading to individual asset characteristics.

### Order Execution & Management

- **Smart Order Types**: Supports standard `Market`, `Limit`, and `Stop` orders, as well as advanced algorithmic orders like `TWAP` (Time-Weighted Average Price) and `VWAP` (Volume-Weighted Average Price).
- **Direct MT5 Trade Execution Bridge**: A dedicated `mt5_order_executor.py` script running on the host subscribes to a RabbitMQ queue, receiving trade orders from the bot and executing them directly in the MT5 terminal.
- **Advanced Trade Management**: The `OrderManager` handles the full trade lifecycle, including position sizing, risk checks, partial exits, and programmatic trailing stops.

### Risk Management

- **Dynamic Position Sizing**: Automatically calculates trade volume based on account balance, risk percentage, and market volatility (e.g., using ATR).
- **Comprehensive Risk Controls**: Implements robust drawdown protection mechanisms and overall risk management strategies to safeguard capital.
- **Profit Management**: Manages profit targets for open positions, including trailing profit targets, to lock in gains.
- **Pre-Trade Compliance**: A `ComplianceManager` module checks every proposed trade against a set of user-defined rules (e.g., max volume, restricted symbols) before execution.

### Strategy Development & Evaluation

- **Backtesting Engine**: A powerful engine supports both vectorized (fast, for simple strategies) and event-driven (slower, for complex logic) backtesting.
- **Strategy Optimization**: Includes an optimization suite to run a strategy with multiple parameter combinations and find the best-performing set.
- **Automated Self-Optimization**: Implements walk-forward optimization to periodically re-optimize strategy parameters using recent market data, ensuring strategies adapt to changing market conditions.
- **Automated Performance Review**: Analyzes trading history, calculates key performance metrics, and can automatically disable underperforming strategies.
- **Performance Analytics**: After a backtest, the system can generate a detailed performance report, including metrics like Sharpe ratio, Sortino ratio, max drawdown, and more.
- **Visualization**: Can plot the equity curve from a backtest to visually assess performance.

## Setup and Installation

1.  **Prerequisites**:

    - Docker & Docker Compose
    - Python 3.11+
    - An installed and running MetaTrader 5 Desktop Terminal.

2.  **Environment File**: Create a `.env` file in the project root. This file must contain the credentials for your MT5 account, database passwords, and any API keys. The project expects encrypted credentials, which can be generated using the functions in `security_utils.py`.

3.  **Python Dependencies**: Install the required Python libraries for the host scripts by running the following command from the project root:

```bash
pip install -r bot/requirements.txt
```

4.  **Build Docker Images**: Build the initial images for all services.
```bash
docker-compose up --build -d
```

## Usage Guide

The system is designed for a streamlined startup process.

### 1. Automated Startup (Recommended)

For an interactive, double-clickable startup, use the `start_interactive.bat` script. This will prompt you for the primary and an optional secondary trading symbol.

**Usage**:

Double-click `start_interactive.bat` and follow the prompts.

Alternatively, for a non-interactive startup, you can use `start_all.bat` directly:

**Usage**:

```bash
start_all.bat <PRIMARY_SYMBOL> [SECONDARY_SYMBOL]
```

**Example**:

```bash
start_all.bat EURUSD
start_all.bat EURUSD XAUUSD
```

These scripts will:
- Launch `data_downloader_api.py` (for historical data priming).
- Launch `mt5_bridge.py` (for live market data).
- Launch `mt5_order_executor.py` (for trade execution).
- Run `docker-compose up -d` (to start all Docker services).
- Execute `docker-compose exec bot python main.py start-trading-session <PRIMARY_SYMBOL> [--secondary-symbol SECONDARY_SYMBOL]` (to start the bot's trading logic).

**To check logs**:
```bash
docker-compose logs -f bot
```

**To stop all services**:
```bash
docker-compose down
```

### 2. Manual Interaction with the Bot via CLI (Advanced)

For advanced debugging or specific commands, you can still interact directly with the bot's CLI inside the running container.

**Example: Fetch Upcoming High-Impact Events**:

```bash
docker-compose exec bot python main.py fetch-economic-events
```

**Example: Check Service Status**:

```bash
docker-compose exec bot python main.py status
```

### 3. Web Interface

The project includes a basic web dashboard that is currently **paused** due to an unresolved Docker environment issue. When fixed, it can be accessed at `http://localhost:5000` after running the `start-web` command:

```bash
docker-compose exec bot python main.py start-web
```
