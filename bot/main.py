import argparse
import time
import threading
import logging
import logging.handlers
import os
from prometheus_client import start_http_server, Counter
from publisher import Publisher
from consumer import Consumer
from influx_connector import InfluxDBConnector
from postgresql_client import PostgreSQLConnector
from order_manager import OrderManager
from security_utils import decrypt_message, get_encryption_key
from historical_data_manager import HistoricalDataManager
from backtesting_engine import BacktestingEngine
from strategies import MovingAverageCrossoverStrategy, RSIStrategy, MACDStrategy, BollingerBandsMeanReversionStrategy, BollingerBandsSqueezeStrategy, DMIADXStrategy, ParabolicSARStrategy, IchimokuStrategy, StochasticOscillatorStrategy, CCIStrategy, ROCStrategy, MomentumStrategy, ATRBreakoutStrategy, KeltnerChannelsStrategy, OBVStrategy, VPTStrategy, ArbitrageStrategy, PairsTradingStrategy, EventDrivenStrategy, IntermarketAwareMovingAverageCrossoverStrategy
from machine_learning_strategy import MachineLearningStrategy
from realtime_strategies import RealtimeMovingAverageCrossoverStrategy, RealtimeSentimentAwareMovingAverageCrossoverStrategy, RealtimeIntermarketAwareMovingAverageCrossoverStrategy, RealtimePatternBasedStrategy, RealtimeThematicStrategy
from news_fetcher import NewsFetcher
from economic_calendar import get_economic_events
from performance_analytics import PerformanceAnalytics
from optimization_suite import OptimizationSuite
from visualizer import Visualizer
from optimization_config import STRATEGY_MAP, PARAM_GRIDS

# Prometheus Metrics
MESSAGES_SENT = Counter('bot_messages_sent_total', 'Total number of messages sent by the bot')

def parse_timeframe_to_minutes(tf_string):
    """Converts a timeframe string (e.g., '5m', '1h', '1d') to minutes."""
    try:
        unit = tf_string[-1].lower()
        if not unit.isalpha():
            raise ValueError("Missing time unit.")
        value_str = tf_string[:-1]
        if not value_str.isdigit():
            raise ValueError("Invalid value.")
        value = int(value_str)
        
        if unit == 'm':
            return value
        elif unit == 'h':
            return value * 60
        elif unit == 'd':
            return value * 24 * 60
        else:
            raise ValueError(f"Unsupported time unit: '{unit}'. Use 'm', 'h', or 'd'.")
    except (ValueError, TypeError, IndexError) as e:
        raise ValueError(f"Invalid timeframe format for '{tf_string}': {e}. Use format like '5m', '1h', '1d'.")


# RabbitMQ Configuration
BROKER_HOST = os.getenv("BROKER_HOST", "rabbitmq")
BROKER_PORT = 5672

def main():
    # Retrieve encryption key from environment
    encryption_key = os.getenv('ENCRYPTION_KEY').encode()
    if not encryption_key:
        logging.error("Initialization failed: ENCRYPTION_KEY environment variable not set.")
        return # Exit if key is not set

    # These values should be encrypted in docker-compose.yml
    encrypted_broker_user = os.getenv("ENCRYPTED_BROKER_USER")
    if encrypted_broker_user:
        BROKER_USER = decrypt_message(encrypted_broker_user.encode(), encryption_key)
    else:
        BROKER_USER = ""

    encrypted_broker_pass = os.getenv("ENCRYPTED_BROKER_PASS")
    if encrypted_broker_pass:
        BROKER_PASS = decrypt_message(encrypted_broker_pass.encode(), encryption_key)
    else:
        BROKER_PASS = ""

    encrypted_influxdb_token = os.getenv("ENCRYPTED_INFLUXDB_TOKEN")
    if encrypted_influxdb_token:
        INFLUXDB_TOKEN = decrypt_message(encrypted_influxdb_token.encode(), encryption_key)
    else:
        INFLUXDB_TOKEN = ""

    INFLUXDB_URL = os.getenv("INFLUXDB_URL")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
    INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

    # PostgreSQL Configuration
    PG_DBNAME = os.getenv("PG_DBNAME")
    PG_HOST = os.getenv("PG_HOST")
    PG_PORT = os.getenv("PG_PORT")
    PG_USER = os.getenv("POSTGRES_USER")
    PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    encrypted_mt5_account = os.getenv("ENCRYPTED_MT5_ACCOUNT")
    if encrypted_mt5_account:
        MT5_ACCOUNT = decrypt_message(encrypted_mt5_account.encode(), encryption_key)
    else:
        MT5_ACCOUNT = ""

    encrypted_mt5_password = os.getenv("ENCRYPTED_MT5_PASSWORD")
    if encrypted_mt5_password:
        MT5_PASSWORD = decrypt_message(encrypted_mt5_password.encode(), encryption_key)
    else:
        MT5_PASSWORD = ""

    MT5_SERVER = os.getenv("MT5_SERVER")

    # Configure logging
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "bot.log")

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10485760, # 10 MB
                backupCount=5
            ),
            logging.StreamHandler() # Also log to console
        ]
    )
    logger = logging.getLogger(__name__)

    # Start Prometheus HTTP server once.
    # If the port is already in use (e.g., by another process like the web UI or another bot instance),
    # it will raise an OSError, which we can safely ignore.
    try:
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000.")
    except OSError as e:
        if e.errno == 98: # Address already in use
            logger.warning("Prometheus port 8000 is already in use. Assuming server is already running.")
        else:
            raise e

    parser = argparse.ArgumentParser(description="MT5 Trading Bot CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check the status of bot services")

    # Send message command
    send_message_parser = subparsers.add_parser("send-message", help="Send a test message via RabbitMQ")
    send_message_parser.add_argument("message", type=str, help="The message to send")
    send_message_parser.add_argument("--loop", action="store_true", help="Continuously send messages for testing retry mechanism")

    # --- Order Management Commands ---
    # Market Order command
    market_order_parser = subparsers.add_parser("market-order", help="Place a market order")
    market_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
    market_order_parser.add_argument("volume", type=float, help="e.g., 0.1")
    market_order_parser.add_argument("requested_price", type=float, help="The price the strategy wants")
    market_order_parser.add_argument("stop_loss", type=float, help="Stop loss price")
    market_order_parser.add_argument("take_profit", type=float, help="Take profit price")
    market_order_parser.add_argument("slippage", type=int, help="Max slippage in points")

    # Limit Order command
    limit_order_parser = subparsers.add_parser("limit-order", help="Place a limit order")
    limit_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
    limit_order_parser.add_argument("volume", type=float, help="e.g., 0.1")
    limit_order_parser.add_argument("price", type=float, help="The limit price")
    limit_order_parser.add_argument("stop_loss", type=float, help="Stop loss price")
    limit_order_parser.add_argument("take_profit", type=float, help="Take profit price")

    # Stop Order command
    stop_order_parser = subparsers.add_parser("stop-order", help="Place a stop order")
    stop_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
    stop_order_parser.add_argument("volume", type=float, help="e.g., 0.1")
    stop_order_parser.add_argument("price", type=float, help="The stop price")
    stop_order_parser.add_argument("stop_loss", type=float, help="Stop loss price")
    stop_order_parser.add_argument("take_profit", type=float, help="Take profit price")

    # TWAP Order command
    twap_order_parser = subparsers.add_parser("twap-order", help="Execute a Time-Weighted Average Price (TWAP) order")
    twap_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
    twap_order_parser.add_argument("total_volume", type=float, help="Total volume to trade")
    twap_order_parser.add_argument("duration_seconds", type=int, help="Duration of the TWAP in seconds")
    twap_order_parser.add_argument("num_chunks", type=int, help="Number of chunks to break the order into")
    twap_order_parser.add_argument("requested_price", type=float, help="The price the strategy wants for each chunk")
    twap_order_parser.add_argument("stop_loss", type=float, help="Stop loss price for each chunk")
    twap_order_parser.add_argument("take_profit", type=float, help="Take profit price for each chunk")
    twap_order_parser.add_argument("slippage", type=int, help="Max slippage in points for each chunk")
    twap_order_parser.add_argument("max_spread", type=int, help="Max spread in points for each chunk")

    # VWAP Order command
    vwap_order_parser = subparsers.add_parser("vwap-order", help="Execute a Volume-Weighted Average Price (VWAP) order")
    vwap_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
    vwap_order_parser.add_argument("total_volume", type=float, help="Total volume to trade")
    vwap_order_parser.add_argument("duration_seconds", type=int, help="Duration of the VWAP in seconds")
    vwap_order_parser.add_argument("num_chunks", type=int, help="Number of chunks to break the order into")
    vwap_order_parser.add_argument("slippage", type=int, help="Max slippage in points for each chunk")
    vwap_order_parser.add_argument("max_spread", type=int, help="Max spread in points for each chunk")

    # Partial Exit command
    partial_exit_parser = subparsers.add_parser("partial-exit", help="Manage partial exit for an open position")
    partial_exit_parser.add_argument("position_id", type=str, help="Identifier for the open position")
    partial_exit_parser.add_argument("percentage_to_close", type=float, help="Percentage of the position volume to close (e.g., 0.25 for 25%)")
    partial_exit_parser.add_argument("current_price", type=float, help="Current market price for the position's symbol")

    # Trailing Stop command
    trailing_stop_parser = subparsers.add_parser("trailing-stop", help="Manage a trailing stop-loss for an open position")
    trailing_stop_parser.add_argument("position_id", type=str, help="Identifier for the open position")
    trailing_stop_parser.add_argument("current_price", type=float, help="The current market price")
    trailing_stop_parser.add_argument("entry_price", type=float, help="The price at which the position was opened")
    trailing_stop_parser.add_argument("current_stop_loss", type=float, help="The current active stop-loss price")
    trailing_stop_parser.add_argument("trailing_step_points", type=int, help="The number of points the price must move favorably to adjust the stop-loss")

    # Time-based Exit command
    time_based_exit_parser = subparsers.add_parser("time-based-exit", help="Manage a time-based exit for an open position")
    time_based_exit_parser.add_argument("position_id", type=str, help="Identifier for the open position")
    time_based_exit_parser.add_argument("reason", type=str, help="Reason for the time-based exit (e.g., 'end_of_day', 'time_limit_reached')")

    # Adjust SL for Volatility command
    adjust_sl_volatility_parser = subparsers.add_parser("adjust-sl-volatility", help="Adjust stop-loss based on volatility (e.g., ATR)")
    adjust_sl_volatility_parser.add_argument("position_id", type=str, help="Identifier for the open position")
    adjust_sl_volatility_parser.add_argument("current_price", type=float, help="The current market price")
    adjust_sl_volatility_parser.add_argument("entry_price", type=float, help="The price at which the position was opened")
    adjust_sl_volatility_parser.add_argument("current_stop_loss", type=float, help="The current active stop-loss price")
    adjust_sl_volatility_parser.add_argument("atr_value", type=float, help="The Average True Range (ATR) value")
    adjust_sl_volatility_parser.add_argument("atr_multiplier", type=float, default=2.0, help="Multiplier for ATR (default: 2.0)")

    # Connect to Broker command
    connect_broker_parser = subparsers.add_parser("connect-broker", help="Connect to the MT5 broker")

    # Check Broker Connection command
    check_broker_connection_parser = subparsers.add_parser("check-broker-connection", help="Check the connection status with the MT5 broker")

    # Reconnect with Backoff command
    reconnect_backoff_parser = subparsers.add_parser("reconnect-with-backoff", help="Attempt to reconnect to a broker with exponential backoff")
    reconnect_backoff_parser.add_argument("broker_id", type=str, help="Identifier for the broker")
    reconnect_backoff_parser.add_argument("--max-retries", type=int, default=5, help="Maximum number of reconnection attempts (default: 5)")
    reconnect_backoff_parser.add_argument("--initial-delay", type=int, default=1, help="Initial delay in seconds before the first retry (default: 1)")

    # Get Account Info command
    get_account_info_parser = subparsers.add_parser("get-account-info", help="Get information about the MT5 trading account")

    # Send InfluxDB data command
    send_influx_data_parser = subparsers.add_parser("send-influx-data", help="Send continuous test data to InfluxDB")
    send_influx_data_parser.add_argument("measurement", type=str, help="The measurement name for InfluxDB data")

    # Reconcile Orders command
    reconcile_orders_parser = subparsers.add_parser("reconcile-orders", help="Reconcile order state with the broker")

    # Send PostgreSQL data command
    send_pg_data_parser = subparsers.add_parser("send-pg-data", help="Send continuous test records to PostgreSQL")
    send_pg_data_parser.add_argument("table", type=str, help="The table name for PostgreSQL data")

    # Calculate Position Size command
    calculate_position_size_parser = subparsers.add_parser("calculate-position-size", help="Calculate dynamic position size based on volatility and risk")
    calculate_position_size_parser.add_argument("symbol", type=str, help="The financial instrument (e.g., EURUSD)")
    calculate_position_size_parser.add_argument("account_balance", type=float, help="The current account balance")
    calculate_position_size_parser.add_argument("risk_per_trade_percent", type=float, help="Percentage of account balance to risk per trade (e.g., 0.01 for 1%)")
    calculate_position_size_parser.add_argument("atr_value", type=float, help="The Average True Range (ATR) value for the instrument")
    calculate_position_size_parser.add_argument("--atr-multiplier", type=float, default=1.0, help="Multiplier for ATR (default: 1.0)")

    # Crash command
    crash_parser = subparsers.add_parser("crash", help="Intentionally crash the bot for testing restart policy")

    # Adjust Position Size Account Based command
    adjust_position_account_parser = subparsers.add_parser("adjust-position-account", help="Adjust position size based on account performance and drawdown")
    adjust_position_account_parser.add_argument("current_account_equity", type=float, help="The current equity in the trading account")
    adjust_position_account_parser.add_argument("initial_account_balance", type=float, help="The initial balance of the trading account")
    adjust_position_account_parser.add_argument("max_drawdown_percent", type=float, help="The maximum allowed drawdown percentage (e.g., 0.10 for 10%)")
    adjust_position_account_parser.add_argument("current_position_size", type=float, help="The current position size in units")

    # Start web interface command
    start_web_parser = subparsers.add_parser("start-web", help="Start the web interface")

    # Implement Drawdown Protection command
    drawdown_protection_parser = subparsers.add_parser("drawdown-protection", help="Implement drawdown protection mechanisms")
    drawdown_protection_parser.add_argument("current_account_equity", type=float, help="The current equity in the trading account")
    drawdown_protection_parser.add_argument("initial_account_balance", type=float, help="The initial balance of the trading account")
    drawdown_protection_parser.add_argument("daily_drawdown_limit_percent", type=float, help="The maximum allowed daily drawdown percentage (e.g., 0.02 for 2%)")
    drawdown_protection_parser.add_argument("total_drawdown_limit_percent", type=float, help="The maximum allowed total drawdown percentage (e.g., 0.10 for 10%)")

    # Manage Comprehensive Risk command
    manage_risk_parser = subparsers.add_parser("manage-risk", help="Manage comprehensive trading risk")
    manage_risk_parser.add_argument("current_portfolio_value", type=float, help="The current total value of the trading portfolio")
    manage_risk_parser.add_argument("max_exposure_percent", type=float, help="The maximum allowed exposure as a percentage (e.g., 0.20 for 20%)")
    manage_risk_parser.add_argument("--stress-test-scenario", type=str, default="moderate", choices=["moderate", "severe"], help="The type of stress test to simulate (default: moderate)")

    # Manage Profit Targets command
    manage_profit_targets_parser = subparsers.add_parser("manage-profit-targets", help="Manage profit targets for an open position")
    manage_profit_targets_parser.add_argument("position_id", type=str, help="Identifier for the open position")
    manage_profit_targets_parser.add_argument("current_price", type=float, help="The current market price")
    manage_profit_targets_parser.add_argument("entry_price", type=float, help="The price at which the position was opened")
    manage_profit_targets_parser.add_argument("profit_target_percent", type=float, help="The profit target as a percentage of the entry price (e.g., 0.02 for 2%)")
    manage_profit_targets_parser.add_argument("trailing_profit_target_percent", type=float, help="The trailing profit target as a percentage (e.g., 0.01 for 1%)")

    # Track Performance command
    track_performance_parser = subparsers.add_parser("track-performance", help="Track and report on the performance of a series of closed trades")

    # Calculate Signal Strength command
    calculate_signal_strength_parser = subparsers.add_parser("calculate-signal-strength", help="Calculate a signal strength score for a given symbol")
    calculate_signal_strength_parser.add_argument("symbol", type=str, help="The financial instrument to analyze (e.g., EURUSD)")

    # Detect Market Regime command
    detect_market_regime_parser = subparsers.add_parser("detect-market-regime", help="Detect the market regime for a given symbol")
    detect_market_regime_parser.add_argument("symbol", type=str, help="The financial instrument to analyze (e.g., EURUSD)")

    # Adjust Parameters for Volatility command
    adjust_parameters_for_volatility_parser = subparsers.add_parser("adjust-parameters-for-volatility", help="Adjust trading parameters based on market volatility")
    adjust_parameters_for_volatility_parser.add_argument("symbol", type=str, help="The financial instrument to analyze (e.g., EURUSD)")
    adjust_parameters_for_volatility_parser.add_argument("market_regime", type=str, help="The current market regime (e.g., Trending, Ranging, Volatile")

    # Generate Seasonality-Aware Signal command
    generate_seasonality_aware_signal_parser = subparsers.add_parser("generate-seasonality-aware-signal", help="Generate a trading signal that is aware of market seasonality")
    generate_seasonality_aware_signal_parser.add_argument("symbol", type=str, help="The financial instrument to analyze (e.g., EURUSD)")
    generate_seasonality_aware_signal_parser.add_argument("current_time", type=str, help="The current time in ISO 8601 format (e.g., \"2025-12-25T10:00:00\")")

    # Get Instrument Profile command
    get_instrument_profile_parser = subparsers.add_parser("get-instrument-profile", help="Get the customized instrument profile for a given symbol")
    get_instrument_profile_parser.add_argument("symbol", type=str, help="The financial instrument to get the profile for (e.g., EURUSD)")

    # Normalize Volatility command
    normalize_volatility_parser = subparsers.add_parser("normalize-volatility", help="Normalize volatility across different assets")
    normalize_volatility_parser.add_argument("symbols", nargs='+', help="A list of symbols to normalize volatility for (e.g., EURUSD USDJPY XAUUSD)")

    # Adjust Position Size for Liquidity command
    adjust_position_size_for_liquidity_parser = subparsers.add_parser("adjust-position-size-for-liquidity", help="Adjust position size based on liquidity")
    adjust_position_size_for_liquidity_parser.add_argument("symbol", type=str, help="The financial instrument to analyze (e.g., EURUSD)")
    adjust_position_size_for_liquidity_parser.add_argument("base_position_size", type=float, help="The base position size before adjustment")

    # Check Trading Hours command
    check_trading_hours_parser = subparsers.add_parser("check-trading-hours", help="Check if trading is allowed for a given symbol at a specific time")
    check_trading_hours_parser.add_argument("symbol", type=str, help="The financial instrument to check (e.g., EURUSD)")
    check_trading_hours_parser.add_argument("--time", type=str, help="Optional: The time to check in ISO 8601 format (e.g., \"2025-12-25T10:00:00\"). Defaults to current time.")

    # Adjust Size for Liquidity command
    adjust_size_for_liquidity_parser = subparsers.add_parser("adjust-size-for-liquidity", help="Adjust position size based on liquidity")
    adjust_size_for_liquidity_parser.add_argument("symbol", type=str, help="The financial instrument to trade (e.g., EURUSD)")
    adjust_size_for_liquidity_parser.add_argument("initial_position_size", type=float, help="The initially calculated position size")

    # Download Historical Data command
    download_data_parser = subparsers.add_parser("download-historical-data", help="Download historical market data")
    download_data_parser.add_argument("symbol", type=str, help="The financial instrument to download (e.g., EURUSD)")
    download_data_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    download_data_parser.add_argument("start_date", type=str, help="The start date for the data in YYYY-MM-DD format")
    download_data_parser.add_argument("end_date", type=str, help="The end date for the data in YYYY-MM-DD format")

    # Fetch News command
    fetch_news_parser = subparsers.add_parser("fetch-news", help="Fetch news and analyze sentiment for a symbol")
    fetch_news_parser.add_argument("symbol", type=str, help="The financial instrument to fetch news for (e.g., EURUSD)")
    fetch_news_parser.add_argument("start_date", type=str, help="The start date for the news in YYYY-MM-DD format")
    fetch_news_parser.add_argument("end_date", type=str, help="The end date for the news in YYYY-MM-DD format")

    # Backtest command
    backtest_parser = subparsers.add_parser("backtest", help="Run a backtest of a trading strategy")
    backtest_parser.add_argument("strategy", type=str, help="The name of the strategy to backtest")
    backtest_parser.add_argument("symbol", type=str, help="The financial instrument to backtest on (e.g., EURUSD)")
    backtest_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    backtest_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
    backtest_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")
    backtest_parser.add_argument("--secondary-symbol", type=str, help="The secondary symbol for intermarket analysis")

    # Backtest Event-Driven command
    backtest_event_parser = subparsers.add_parser("backtest-event", help="Run an event-driven backtest of a trading strategy")
    backtest_event_parser.add_argument("symbol", type=str, help="The financial instrument to backtest on (e.g., EURUSD)")
    backtest_event_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    backtest_event_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
    backtest_event_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")

    # Backtest Pairs command
    backtest_pairs_parser = subparsers.add_parser("backtest-pairs", help="Run a backtest of a pairs trading strategy")
    backtest_pairs_parser.add_argument("strategy", type=str, help="The name of the pairs strategy to backtest (e.g., pairs_trading, arbitrage)")
    backtest_pairs_parser.add_argument("symbol_a", type=str, help="The first financial instrument in the pair")
    backtest_pairs_parser.add_argument("symbol_b", type=str, help="The second financial instrument in the pair")
    backtest_pairs_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    backtest_pairs_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
    backtest_pairs_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")

    # Performance Analytics command
    performance_analytics_parser = subparsers.add_parser("analyze-performance", help="Run performance analytics on a set of trades")

    # Optimization command
    optimization_parser = subparsers.add_parser("optimize", help="Run a strategy optimization")
    optimization_parser.add_argument("strategy", type=str, help="The name of the strategy to optimize")
    optimization_parser.add_argument("symbol", type=str, help="The financial instrument to optimize on (e.g., EURUSD)")
    optimization_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    optimization_parser.add_argument("start_date", type=str, help="The start date for the optimization in YYYY-MM-DD format")
    optimization_parser.add_argument("end_date", type=str, help="The end date for the optimization in YYYY-MM-DD format")

    # Detect Patterns command
    detect_patterns_parser = subparsers.add_parser("detect-patterns", help="Detect candlestick patterns in historical data")
    detect_patterns_parser.add_argument("symbol", type=str, help="The financial instrument to analyze (e.g., EURUSD)")
    detect_patterns_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")

    # Backtest ML command
    backtest_ml_parser = subparsers.add_parser("backtest-ml", help="Run a backtest of a machine learning strategy")
    backtest_ml_parser.add_argument("symbol", type=str, help="The financial instrument to backtest on (e.g., EURUSD)")
    backtest_ml_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    backtest_ml_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
    backtest_ml_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")

    # Plot Performance command
    plot_performance_parser = subparsers.add_parser("plot-performance", help="Plot the performance of a backtest from portfolio_history.csv")

    # Walk-Forward Optimize command
    walk_forward_optimize_parser = subparsers.add_parser("walk-forward-optimize", help="Run walk-forward optimization to update strategy parameters")
    walk_forward_optimize_parser.add_argument("strategy", type=str, help="The name of the strategy to optimize")
    walk_forward_optimize_parser.add_argument("symbol", type=str, help="The financial instrument to optimize on (e.g., EURUSD)")
    walk_forward_optimize_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    walk_forward_optimize_parser.add_argument("window_days", type=int, help="The number of recent days to use for optimization")

    # Performance Review command
    performance_review_parser = subparsers.add_parser("performance-review", help="Run automated performance review to disable underperforming strategies")

    # Strategy Discovery command
    strategy_discovery_parser = subparsers.add_parser("strategy-discovery", help="Run genetic algorithm to discover new trading strategies")
    strategy_discovery_parser.add_argument("symbol", type=str, help="The financial instrument to use for discovery (e.g., EURUSD)")
    strategy_discovery_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    strategy_discovery_parser.add_argument("--population", type=int, default=50, help="Population size for GA")
    strategy_discovery_parser.add_argument("--generations", type=int, default=10, help="Number of generations")

    # Test Sentiment command
    test_sentiment_parser = subparsers.add_parser("test-sentiment", help="Test sentiment integration")
    test_sentiment_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
    test_sentiment_parser.add_argument("timeframe", type=str, help="e.g., D1")
    test_sentiment_parser.add_argument("start_date", type=str, help="e.g., 2023-01-01")
    test_sentiment_parser.add_argument("end_date", type=str, help="e.g., 2023-12-31")

    

    # Start Trading Session command
    start_trading_session_parser = subparsers.add_parser("start-trading-session", help="Start a dynamic real-time trading session using the StrategySelector.")
    start_trading_session_parser.add_argument("symbol", type=str, help="The primary symbol to trade (e.g., EURUSD)")
    start_trading_session_parser.add_argument("--secondary-symbol", type=str, help="An optional secondary symbol for intermarket analysis.")
    start_trading_session_parser.add_argument("--correlation-window-minutes", type=int, help="The correlation window in minutes (e.g., 60). Required if --secondary-symbol is used.")
    start_trading_session_parser.add_argument("--candle-interval-minutes", type=int, default=1, help="The interval in minutes for aggregating ticks into candles (default: 1)")

    # Economic Calendar command
    economic_calendar_parser = subparsers.add_parser("fetch-economic-events", help="Fetch and display upcoming economic events")
    economic_calendar_parser.add_argument("--days", type=int, default=7, help="Number of days ahead to fetch events for (default: 7)")

    args = parser.parse_args()

    order_manager = None
    if args.command not in ["start-trading-session", "status", "send-message", "start-web", "fetch-economic-events"]:
        order_manager = OrderManager()

    if args.command == "status":
        logger.info("Checking bot service status...")
        # Check RabbitMQ connection
        try:
            publisher = Publisher(BROKER_HOST, BROKER_PORT, BROKER_USER, BROKER_PASS)
            publisher.connect()
            logger.info("RabbitMQ: Connected")
            publisher.close()
        except Exception as e:
            logger.error(f"RabbitMQ: Connection failed - {e}")

        # Check InfluxDB connection
        try:
            influx_connector = InfluxDBConnector(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG, bucket=INFLUXDB_BUCKET)
            influx_connector.write_data(measurement="status_check", tags={"service": "bot"}, fields={"status": 1})
            logger.info("InfluxDB: Connected and writable")
            influx_connector.close()
        except Exception as e:
            logger.error(f"InfluxDB: Connection failed - {e}")

        # Check PostgreSQL connection
        try:
            pg_connector = PostgreSQLConnector(
                dbname=PG_DBNAME,
                user=PG_USER,
                password=PG_PASSWORD,
                host=PG_HOST,
                port=PG_PORT
            )
            pg_connector.connect()
            if pg_connector.conn:
                logger.info("PostgreSQL: Connected")
                pg_connector.close()
            else:
                logger.error("PostgreSQL: Connection failed")
        except Exception as e:
            logger.error(f"PostgreSQL: Connection failed - {e}")

    elif args.command == "send-message":
        if args.loop:
            logger.info(f"Starting continuous message sending loop with message: {args.message}")
            publisher = Publisher(BROKER_HOST, BROKER_PORT, BROKER_USER, BROKER_PASS)
            while True:
                try:
                    publisher.connect()
                    publisher.publish_message("test_queue", args.message)
                    MESSAGES_SENT.inc()
                    logger.info("Message sent successfully.")
                except Exception as e:
                    logger.error(f"Failed to send message: {e}")
                time.sleep(2)
        else:
            logger.info(f"Sending message: {args.message}")
            try:
                publisher = Publisher(BROKER_HOST, BROKER_PORT, BROKER_USER, BROKER_PASS)
                publisher.connect()
                publisher.publish_message("test_queue", args.message)
                logger.info("Message sent successfully.")
                publisher.close()
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

    elif args.command in ["market-order", "limit-order", "stop-order"]:
        if args.command == "market-order":
            logger.info(f"Executing market order command for {args.symbol}")
            order_manager.place_market_order(args.symbol, args.volume, args.requested_price, args.stop_loss, args.take_profit, args.slippage)
        elif args.command == "limit-order":
            logger.info(f"Executing limit order command for {args.symbol}")
            order_manager.place_limit_order(args.symbol, args.volume, args.price, args.stop_loss, args.take_profit)
        elif args.command == "stop-order":
            logger.info(f"Executing stop order command for {args.symbol}")
            order_manager.place_stop_order(args.symbol, args.volume, args.price, args.stop_loss, args.take_profit)

    elif args.command == "twap-order":
        logger.info(f"Executing TWAP order command for {args.symbol}")
        order_manager.place_twap_order(
            symbol=args.symbol,
            total_volume=args.total_volume,
            duration_seconds=args.duration_seconds,
            num_chunks=args.num_chunks,
            requested_price=args.requested_price,
            stop_loss=args.stop_loss,
            take_profit=args.take_profit,
            slippage=args.slippage,
            max_spread=args.max_spread
        )

    elif args.command == "vwap-order":
        logger.info(f"Executing VWAP order command for {args.symbol}")
        order_manager.place_vwap_order(
            symbol=args.symbol,
            total_volume=args.total_volume,
            duration_seconds=args.duration_seconds,
            num_chunks=args.num_chunks,
            slippage=args.slippage,
            max_spread=args.max_spread
        )

    elif args.command == "partial-exit":
        logger.info(f"Executing partial exit command for position {args.position_id}")
        order_manager.manage_partial_exit(
            position_id=args.position_id,
            percentage_to_close=args.percentage_to_close,
            current_price=args.current_price
        )

    elif args.command == "trailing-stop":
        logger.info(f"Executing trailing stop command for position {args.position_id}")
        order_manager.manage_trailing_stop(
            position_id=args.position_id,
            current_price=args.current_price,
            entry_price=args.entry_price,
            current_stop_loss=args.current_stop_loss,
            trailing_step_points=args.trailing_step_points
        )

    elif args.command == "time-based-exit":
        logger.info(f"Executing time-based exit command for position {args.position_id}")
        order_manager.manage_time_based_exit(
            position_id=args.position_id,
            reason=args.reason
        )

    elif args.command == "adjust-sl-volatility":
        logger.info(f"Executing adjust SL for volatility command for position {args.position_id}")
        order_manager.adjust_sl_for_volatility(
            position_id=args.position_id,
            current_price=args.current_price,
            entry_price=args.entry_price,
            current_stop_loss=args.current_stop_loss,
            atr_value=args.atr_value,
            atr_multiplier=args.atr_multiplier
        )

    elif args.command == "connect-broker":
        logger.info(f"Executing connect to broker command")
        order_manager.connect_to_broker()

    elif args.command == "check-broker-connection":
        logger.info(f"Executing check broker connection command")
        order_manager.check_broker_connection()

    elif args.command == "get-account-info":
        logger.info(f"Executing get account info command")
        order_manager.get_account_info()

    elif args.command == "start-web":
        logger.info("Starting web interface...")
        from web_interface import app
        app.run(host='0.0.0.0', port=5000)

    elif args.command == "reconcile-orders":
        logger.info(f"Executing reconcile orders command")
        order_manager.reconcile_order_state()

    elif args.command == "send-influx-data":
        logger.info(f"Starting continuous InfluxDB data sending for measurement: {args.measurement}")
        influx_connector = InfluxDBConnector(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG, bucket=INFLUXDB_BUCKET)
        counter = 0
        while True:
            try:
                tags = {"source": "bot_test"}
                fields = {"value": counter}
                influx_connector.write_data(args.measurement, tags, fields)
                counter += 1
                time.sleep(1)
            except Exception as e:
                logger.error(f"Failed to send InfluxDB data: {e}")
                time.sleep(5)

    elif args.command == "send-pg-data":
        logger.info(f"Starting continuous PostgreSQL data sending for table: {args.table}")
        pg_connector = PostgreSQLConnector(
            dbname=PG_DBNAME,
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )
        counter = 0
        while True:
            try:
                pg_connector.connect()
                columns = {"id": "SERIAL PRIMARY KEY", "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "value": "INTEGER"}
                pg_connector.create_table(args.table, columns)
                data = {"value": counter}
                pg_connector.insert_data(args.table, data)
                logger.info(f"Data inserted into {args.table}: {data}")
                counter += 1
            except Exception as e:
                logger.error(f"Failed to send PostgreSQL data: {e}")
            finally:
                pg_connector.close()
            time.sleep(1)

    elif args.command == "calculate-position-size":
        logger.info(f"Executing calculate position size command for {args.symbol}")
        order_manager.calculate_dynamic_position_size(
            symbol=args.symbol,
            account_balance=args.account_balance,
            risk_per_trade_percent=args.risk_per_trade_percent,
            atr_value=args.atr_value,
            atr_multiplier=args.atr_multiplier
        )

    elif args.command == "adjust-position-account":
        logger.info(f"Executing adjust position size account based command for equity {args.current_account_equity}")
        order_manager.adjust_position_size_account_based(
            current_account_equity=args.current_account_equity,
            initial_account_balance=args.initial_account_balance,
            max_drawdown_percent=args.max_drawdown_percent,
            current_position_size=args.current_position_size
        )

    elif args.command == "manage-risk":
        logger.info(f"Executing manage risk command for portfolio value {args.current_portfolio_value}")
        order_manager.manage_comprehensive_risk(
            current_portfolio_value=args.current_portfolio_value,
            max_exposure_percent=args.max_exposure_percent,
            stress_test_scenario=args.stress_test_scenario
        )

    elif args.command == "drawdown-protection":
        logger.info(f"Executing drawdown protection command for equity {args.current_account_equity}")
        order_manager.implement_drawdown_protection(
            current_account_equity=args.current_account_equity,
            initial_account_balance=args.initial_account_balance,
            daily_drawdown_limit_percent=args.daily_drawdown_limit_percent,
            total_drawdown_limit_percent=args.total_drawdown_limit_percent
        )

    elif args.command == "manage-profit-targets":
        logger.info(f"Executing manage profit targets command for position {args.position_id}")
        order_manager.manage_profit_targets(
            position_id=args.position_id,
            current_price=args.current_price,
            entry_price=args.entry_price,
            profit_target_percent=args.profit_target_percent,
            trailing_profit_target_percent=args.trailing_profit_target_percent
        )

    elif args.command == "track-performance":
        logger.info("Executing track performance command")
        order_manager.track_performance()

    elif args.command == "calculate-signal-strength":
        logger.info(f"Executing calculate signal strength command for {args.symbol}")
        order_manager.calculate_signal_strength(args.symbol)

    elif args.command == "detect-market-regime":
        logger.info(f"Executing detect market regime command for {args.symbol}")
        order_manager.detect_market_regime(args.symbol)

    elif args.command == "adjust-parameters-for-volatility":
        logger.info(f"Executing adjust parameters for volatility command for {args.symbol}")
        order_manager.adjust_parameters_for_volatility(args.symbol, args.market_regime)

    elif args.command == "generate-seasonality-aware-signal":
        logger.info(f"Executing generate seasonality-aware signal command for {args.symbol}")
        order_manager.generate_seasonality_aware_signal(args.symbol, args.current_time)

    elif args.command == "get-instrument-profile":
        logger.info(f"Executing get instrument profile command for {args.symbol}")
        order_manager.get_instrument_profile(args.symbol)

    elif args.command == "normalize-volatility":
        logger.info("Executing normalize volatility command")
        order_manager.normalize_volatility(args.symbols)

    elif args.command == "adjust-position-size-for-liquidity":
        logger.info(f"Executing adjust position size for liquidity command for {args.symbol}")
        order_manager.adjust_position_size_for_liquidity(args.symbol, args.base_position_size)

    elif args.command == "check-trading-hours":
        logger.info(f"Executing check trading hours command for {args.symbol}")
        import datetime # Import datetime here to avoid circular dependency if it's not already imported
        check_time = None
        if args.time:
            try:
                check_time = datetime.datetime.fromisoformat(args.time)
            except ValueError:
                logger.error("Invalid time format. Please use ISO 8601 format (YYYY-MM-DDTHH:MM:SS).")
                return
        order_manager.is_trading_hours_allowed(args.symbol, check_time)

    elif args.command == "download-historical-data":
        logger.info("To download historical data, please run the following command on your host machine (not in Docker):")
        logger.info(f"python historical_data_importer.py {args.symbol} {args.timeframe} {args.start_date} {args.end_date}")

    elif args.command == "fetch-news":
        logger.info(f"Executing fetch news command for {args.symbol}")
        news_fetcher = NewsFetcher()
        news_df = news_fetcher.fetch_news_and_analyze_sentiment(args.symbol, args.start_date, args.end_date)
        news_fetcher.save_events_to_csv(news_df)

    elif args.command == "backtest":
        logger.info(f"Executing backtest command for {args.symbol} with strategy {args.strategy}")
        historical_data_manager = HistoricalDataManager()
        data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)

        if data is None:
            logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")
            return

        strategy_name = args.strategy.lower()
        strategy = None

        if strategy_name == 'moving_average_crossover':
            strategy = MovingAverageCrossoverStrategy()
        elif strategy_name == 'rsi':
            strategy = RSIStrategy()
        elif strategy_name == 'macd':
            strategy = MACDStrategy()
        elif strategy_name == 'bollinger_bands_mean_reversion':
            strategy = BollingerBandsMeanReversionStrategy()
        elif strategy_name == 'bollinger_bands_squeeze':
            strategy = BollingerBandsSqueezeStrategy()
        elif strategy_name == 'dmi_adx':
            strategy = DMIADXStrategy()
        elif strategy_name == 'parabolic_sar':
            strategy = ParabolicSARStrategy()
        elif strategy_name == 'ichimoku':
            strategy = IchimokuStrategy()
        elif strategy_name == 'stochastic_oscillator':
            strategy = StochasticOscillatorStrategy()
        elif strategy_name == 'cci':
            strategy = CCIStrategy()
        elif strategy_name == 'roc':
            strategy = ROCStrategy()
        elif strategy_name == 'momentum':
            strategy = MomentumStrategy()
        elif strategy_name == 'atr_breakout':
            strategy = ATRBreakoutStrategy()
        elif strategy_name == 'keltner_channels':
            strategy = KeltnerChannelsStrategy()
        elif strategy_name == 'obv':
            strategy = OBVStrategy()
        elif strategy_name == 'vpt':
            strategy = VPTStrategy()
        elif strategy_name == 'intermarket_aware_moving_average_crossover':
            if not args.secondary_symbol:
                logger.error("The intermarket aware strategy requires a secondary symbol. Please provide one with --secondary-symbol.")
                return
            secondary_data = historical_data_manager.load_data_from_csv(args.secondary_symbol, args.timeframe)
            if secondary_data is None:
                logger.error(f"Could not load historical data for secondary symbol {args.secondary_symbol} ({args.timeframe}). Please download it first.")
                return
            strategy = IntermarketAwareMovingAverageCrossoverStrategy()
            backtesting_engine = BacktestingEngine(strategy, data, historical_data_b=secondary_data)
            backtesting_engine.run_backtest()
            return
        elif strategy_name in ['arbitrage', 'pairs_trading']:
            logger.error(f"The '{strategy_name}' strategy requires two symbols. Please use the 'backtest-pairs' command.")
            return
        else:
            logger.error(f"Unknown strategy: {strategy_name}")
            return
            
        backtesting_engine = BacktestingEngine(strategy, data)
        backtesting_engine.run_backtest()

    elif args.command == "backtest-event":
        logger.info(f"Executing event-driven backtest for {args.symbol}")
        historical_data_manager = HistoricalDataManager()
        data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)

        if data is None:
            logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")
            return

        data.name = args.symbol  # Set the symbol name for the backtesting engine
        strategy = EventDrivenStrategy()
        backtesting_engine = BacktestingEngine(strategy, data)
        backtesting_engine.run_backtest()

    elif args.command == "backtest-pairs":
        logger.info(f"Executing backtest-pairs command for {args.symbol_a} and {args.symbol_b} with strategy {args.strategy}")
        historical_data_manager = HistoricalDataManager()
        data_a = historical_data_manager.load_data_from_csv(args.symbol_a, args.timeframe)
        data_b = historical_data_manager.load_data_from_csv(args.symbol_b, args.timeframe)

        if data_a is None or data_b is None:
            logger.error(f"Could not load historical data for one or both symbols. Please download them first.")
            return

        strategy_name = args.strategy.lower()
        strategy = None

        if strategy_name == 'arbitrage':
            strategy = ArbitrageStrategy()
        elif strategy_name == 'pairs_trading':
            strategy = PairsTradingStrategy()
        else:
            logger.error(f"Unknown or unsupported pairs strategy: {strategy_name}")
            return
            
        backtesting_engine = BacktestingEngine(strategy, data_a, historical_data_b=data_b)
        backtesting_engine.run_backtest()

    elif args.command == "backtest-ml":
        logger.info(f"Executing backtest-ml command for {args.symbol}")
        historical_data_manager = HistoricalDataManager()
        data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)

        if data is None:
            logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")
            return

        ml_strategy = MachineLearningStrategy()
        X, y = ml_strategy.prepare_data(data.copy())
        ml_strategy.train_model(X, y)

        backtesting_engine = BacktestingEngine(ml_strategy, data)
        backtesting_engine.run_backtest()

    elif args.command == "analyze-performance":
        logger.info(f"Executing analyze-performance command")
        analytics = PerformanceAnalytics(trades_filepath="trades.csv")
        analytics.run()

    elif args.command == "optimize":
        logger.info(f"Executing optimize command for {args.symbol} with strategy {args.strategy}")
        
        # 1. Load Data
        historical_data_manager = HistoricalDataManager()
        data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)
        if data is None:
            logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")
            return

        strategy_name = args.strategy.lower()
        strategy_class = STRATEGY_MAP.get(strategy_name)

        if not strategy_class:
            logger.error(f"Unknown or unsupported strategy for optimization: {strategy_name}")
            return

        param_grid = PARAM_GRIDS.get(strategy_name)

        # 3. Run Optimization
        optimizer = OptimizationSuite(strategy_class, data, param_grid)
        optimizer.run_optimization()

    elif args.command == "detect-patterns":
        logger.info(f"Executing detect-patterns command for {args.symbol}")
        historical_data_manager = HistoricalDataManager()
        data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)
        if data is not None:
            from candle_pattern_detector import CandlePatternDetector
            pattern_detector = CandlePatternDetector(data)
            patterns_df = pattern_detector.detect()
            logger.info("Candlestick patterns identified:")
            
            found_any = False
            for date, patterns in patterns_df.items():
                if patterns:
                    found_any = True
                    logger.info(f"--- {date.strftime('%Y-%m-%d')} ---")
                    for pattern in patterns:
                        logger.info(f"  - {pattern.replace('_', ' ').title()}")
            
            if not found_any:
                logger.info("No patterns detected in the provided data.")
        else:
            logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")

    elif args.command == "adjust-size-for-liquidity":
        logger.info(f"Executing adjust size for liquidity command for {args.symbol}")
        order_manager.adjust_size_for_liquidity(args.symbol, args.initial_position_size)

    elif args.command == "crash":
        logger.critical("Intentionally crashing the bot...")
        raise Exception("Intentional crash!")

    elif args.command == "plot-performance":
        logger.info(f"Executing plot-performance command")
        visualizer = Visualizer()
        visualizer.load_data()
        visualizer.plot_equity_curve()

    elif args.command == "walk-forward-optimize":
        logger.info(f"Executing walk-forward-optimize command for {args.strategy} on {args.symbol}")
        historical_data_manager = HistoricalDataManager()
        data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)
        if data is None:
            logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")
            return

        strategy_name = args.strategy.lower()
        strategy_class = STRATEGY_MAP.get(strategy_name)
        if not strategy_class:
            logger.error(f"Unknown strategy: {strategy_name}")
            return

        param_grid = PARAM_GRIDS.get(strategy_name)
        window_size = len(data) if args.window_days >= len(data) else args.window_days * (len(data) // args.window_days)  # Approximate days to rows

        optimizer = OptimizationSuite(strategy_class, data, param_grid)
        optimizer.run_walk_forward_optimization(strategy_name, window_size)

    elif args.command == "performance-review":
        logger.info("Executing performance-review command")
        from performance_review import PerformanceReviewer
        reviewer = PerformanceReviewer()
        reviewer.analyze_performance()

    elif args.command == "strategy-discovery":
        logger.info(f"Executing strategy-discovery command for {args.symbol}")
        historical_data_manager = HistoricalDataManager()
        data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)
        if data is None:
            logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")
            return

        from genetic_algorithm import GeneticStrategyDiscovery
        ga = GeneticStrategyDiscovery(data, population_size=args.population, generations=args.generations)
        best_individual, best_fitness = ga.discover()
        logger.info(f"Discovered strategy: {best_individual} with fitness {best_fitness}")

        # If fitness > threshold, add to config
        if best_fitness > 0.5:  # Example threshold
            logger.info("Promoting discovered strategy to active arsenal.")
            # Add to STRATEGY_MAP or something, but for now, just log
            # TODO: Implement promotion

    elif args.command == "test-sentiment":
        logger.info(f"Executing test-sentiment command for {args.symbol}")
        import pandas as pd
        historical_data_manager = HistoricalDataManager()
        data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)

        if data is None:
            logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")
            return

        news_fetcher = NewsFetcher()
        sentiment_data = news_fetcher.fetch_news_and_analyze_sentiment(args.symbol, args.start_date, args.end_date)

        if sentiment_data is not None and not sentiment_data.empty:
            data.index = pd.to_datetime(data.index)
            sentiment_data['timestamp'] = pd.to_datetime(sentiment_data['timestamp'])
            sentiment_data.set_index('timestamp', inplace=True)
            
            # Resample sentiment data to match the data's index (e.g., daily)
            if not data.index.freq:
                inferred_freq = pd.infer_freq(data.index)
                if inferred_freq:
                    data.index.freq = inferred_freq
                else:
                    logger.error("Could not infer frequency from data index.")
                    return
            
            sentiment_data = sentiment_data.resample(data.index.freq).mean().ffill()

            merged_data = data.join(sentiment_data['sentiment'])
            merged_data['sentiment'].fillna(0, inplace=True)

            logger.info(f"Merged data head:\n{merged_data.head()}")
            logger.info(f"Merged data tail:\n{merged_data.tail()}")
        else:
            logger.info("No sentiment data found.")

    

    elif args.command == "start-trading-session":
        # The 'strategy' argument is now obsolete. The StrategySelector handles this.
        logger.info(f"Starting dynamic trading session for {args.symbol}")

        # The correlation window is still needed for the MarketContextAnalyzer,
        # so we retrieve it if the secondary symbol is provided.
        correlation_window_minutes = None
        if args.secondary_symbol:
            if not args.correlation_window_minutes:
                logger.error("Intermarket analysis requires a correlation window. Use --correlation-window-minutes (e.g., 60).")
                return
            correlation_window_minutes = args.correlation_window_minutes
            logger.info(f"Using correlation window: {correlation_window_minutes} minutes for intermarket analysis.")

        consumer = Consumer(
            host=BROKER_HOST,
            port=BROKER_PORT,
            username=BROKER_USER,
            password=BROKER_PASS,
            symbol=args.symbol,
            secondary_symbol=args.secondary_symbol,
            correlation_window_minutes=correlation_window_minutes,
            candle_interval_minutes=args.candle_interval_minutes
        )

        consumer.connect()
        consumer.start_consuming("realtime_data")

    elif args.command == "fetch-economic-events":
        logger.info(f"Executing fetch-economic-events command for the next {args.days} days...")
        events_df = get_economic_events(days_ahead=args.days)
        if not events_df.empty:
            logger.info("Upcoming Economic Events:")
            # Print the dataframe in a readable format to the console
            print(events_df[['date', 'time', 'currency', 'event', 'importance']].to_string())
        else:
            logger.warning("Could not fetch any economic events or no events are scheduled.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
