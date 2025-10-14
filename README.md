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

- **Containerized Environment**: All core services (bot logic, databases, message queue) are containerized with Docker for consistent and reproducible deployments.
- **Modular Architecture**: The code is separated into distinct modules for data management, strategies, execution, analytics, and more, allowing for easy extension.
- **Secure Configuration**: All sensitive credentials (broker details, API keys) are encrypted and managed via environment variables.

### Redundancy & Reliability

- **Resilient Connections**: All connections to external services (PostgreSQL, InfluxDB, RabbitMQ) are wrapped in a custom retry decorator (`@retry_with_backoff`) that handles connection failures with exponential backoff and jitter, preventing crashes due to transient network issues.
- **Persistent Consumer**: The core `Consumer` that processes market data is built within a resilient loop. If the connection to the RabbitMQ broker is lost, it will automatically and indefinitely attempt to reconnect without crashing the bot.
- **Data Feed Watchdog**: A standalone `mt5_watchdog.py` script runs on the host machine to monitor the critical `mt5_bridge.py` process. It listens for a heartbeat and checks the process status, automatically restarting the bridge if it fails.

### Market Analysis & Context

- **Live MT5 Integration**: Connects directly to a live MT5 terminal for both real-time tick data and for downloading historical data for backtesting.
- **News & Sentiment Analysis**: Integrates with a news API to fetch financial news for specified symbols and performs sentiment analysis. This sentiment score can be used by strategies to make more informed decisions.
- **Economic Calendar Awareness**: The bot fetches a calendar of high-impact economic events. It can be configured to automatically pause trading during a quiet period before and after these events to avoid extreme volatility.
- **Intermarket Analysis**: Strategies can be configured to use data from a secondary symbol (e.g., a market index or a correlated asset) to provide additional context for trading signals.

### Order Execution & Management

- **Smart Order Types**: Supports standard `Market`, `Limit`, and `Stop` orders, as well as advanced algorithmic orders like `TWAP` (Time-Weighted Average Price) and `VWAP` (Volume-Weighted Average Price).
- **Advanced Trade Management**: Provides functionality for complex trade actions, including partial exits and programmatic trailing stops.

### Risk Management

- **Dynamic Position Sizing**: Automatically calculates trade volume based on account balance, risk percentage, and market volatility (e.g., using ATR).
- **Drawdown Protection**: Includes logic to monitor account equity and enforce rules against daily and total drawdown limits.
- **Pre-Trade Compliance**: A `ComplianceManager` module checks every proposed trade against a set of user-defined rules (e.g., max volume, restricted symbols) before execution.

### Strategy Development & Evaluation

- **Backtesting Engine**: A powerful engine supports both vectorized (fast, for simple strategies) and event-driven (slower, for complex logic) backtesting.
- **Strategy Optimization**: Includes an optimization suite to run a strategy with multiple parameter combinations and find the best-performing set.
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
