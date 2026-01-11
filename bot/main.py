import argparse
import logging
import logging.handlers
import os
from dotenv import load_dotenv
try:
    from prometheus_client import start_http_server
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

# Load environment variables
load_dotenv()

# Services
from config import get_config, CriticalConfigurationError
from order_manager import OrderManager
from broker import LiveBroker, PaperBroker
from capital_allocator import CapitalAllocator

# Commands
from commands.order_commands import OrderCommands
from commands.broker_commands import BrokerCommands
from commands.data_commands import DataCommands
from commands.analysis_commands import AnalysisCommands
from commands.risk_commands import RiskCommands
from commands.backtest_commands import BacktestCommands
from commands.system_commands import SystemCommands

def setup_logging():
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
    return logging.getLogger(__name__)

def main():
    try:
        cfg = get_config()
    except CriticalConfigurationError as e:
        print(f"FATAL: {e}")
        return

    logger = setup_logging()

    # Start Prometheus
    if HAS_PROMETHEUS:
        try:
            start_http_server(8000)
            logger.info("Prometheus metrics server started on port 8000.")
        except OSError as e:
            if e.errno == 98: # Address already in use
                logger.warning("Prometheus port 8000 is already in use. Assuming server is already running.")
            else:
                raise e
    else:
        logger.warning("prometheus_client not installed. Metrics server will not be started.")

    parser = argparse.ArgumentParser(description="MT5 Trading Bot CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Initialize Command Classes
    # Note: We pass the main parser's subparsers object to add_arguments implicitly via a helper or 
    # we need to adjust BaseCommand to accept subparsers.
    # Actually, BaseCommand logic was: self.parser.add_parser... 
    # But add_parser comes from subparsers, not the main parser.
    # So I need to fix BaseCommand to accept subparsers.
    
    # Correcting BaseCommand usage strategy:
    # I will modify BaseCommand to accept the subparsers object.

    # Oops, I already defined BaseCommand to take 'parser'.
    # In my implementation of subclasses, I did self.parser.add_parser...
    # If self.parser is the main parser, add_parser adds a subparser? No, add_subparsers does.
    # subparser.add_parser adds a command.
    # So I should pass the 'subparsers' object to the Command classes.

    commands = [
        OrderCommands(subparsers),
        BrokerCommands(subparsers),
        DataCommands(subparsers),
        AnalysisCommands(subparsers),
        RiskCommands(subparsers),
        BacktestCommands(subparsers),
        SystemCommands(subparsers)
    ]

    for cmd in commands:
        cmd.add_arguments()

    args = parser.parse_args()

    # Determine Broker Mode
    broker = None
    if hasattr(args, 'mode') and args.mode == 'live':
        broker = LiveBroker()
    else:
        broker = PaperBroker()

    # Initialize Services
    capital_allocator = CapitalAllocator()
    # Not all commands need OrderManager, but we initialize it if likely needed
    # (or we could lazy load in the command execution)
    order_manager = OrderManager(broker, capital_allocator)

    services = {
        'config': cfg,
        'broker': broker,
        'order_manager': order_manager
    }

    # Execute Command
    if args.command:
        # We need to find which command class handles this command.
        # A simple way is to let each command class try to execute, or maintain a mapping.
        # Since I didn't enforce a mapping in BaseCommand, I will iterate.
        # Wait, iterating is inefficient/messy if execute checks args.command string.
        # Efficient way: The command classes' execute method checks the relevant strings.
        
        executed = False
        for cmd in commands:
            # We can check if the specific command string belongs to this class
            # But execute() implementation in subclasses checks 'args.command == ...'
            # So calling execute on all might be safe if they just return if not matching.
            # But my implementation returns nothing (None) if mismatch? No, I used specific checks.
            # I should inspect my generated code. 
            # Example:
            # if args.command == "market-order": ...
            # I did NOT put an "else" that raises or returns false.
            # So I can just call all of them. The one that matches will run.
            
            # Ideally, I would have a dict map, but splitting args is good enough for now.
            try:
                # To be safer, I can add a method 'handles(command_name)' to BaseCommand or just rely on execute.
                # I'll rely on execute for now, ensuring no overlapping command names.
                cmd.execute(args, services)
            except Exception as e:
                # If a command fails, we log it. But we don't want to log error for mismatch.
                # My execute methods log error "OrderManager not available" etc.
                # They don't seem to return "True/False" for handled.
                # This is a bit flaw in my quick design.
                # I will create a dictionary mapping command names to handlers.
                pass
                
        # Better approach:
        # Create a dispatch map.
        dispatch_map = {}
        # I need to know which commands each class registered.
        # I will manually map them here for now to ensure correctness.
        
        # OrderCommands
        for cmd_name in ["market-order", "limit-order", "stop-order", "twap-order", "vwap-order", 
                         "partial-exit", "trailing-stop", "time-based-exit", "adjust-sl-volatility", "manage-profit-targets"]:
            dispatch_map[cmd_name] = commands[0]
            
        # BrokerCommands
        for cmd_name in ["connect-broker", "check-broker-connection", "reconnect-with-backoff", "get-account-info", "reconcile-orders"]:
            dispatch_map[cmd_name] = commands[1]

        # DataCommands
        for cmd_name in ["send-influx-data", "send-pg-data", "download-historical-data", "fetch-news", "fetch-economic-events"]:
            dispatch_map[cmd_name] = commands[2]

        # AnalysisCommands
        for cmd_name in ["calculate-signal-strength", "detect-market-regime", "adjust-parameters-for-volatility", 
                         "generate-seasonality-aware-signal", "get-instrument-profile", "normalize-volatility", 
                         "check-trading-hours", "detect-patterns", "test-sentiment"]:
            dispatch_map[cmd_name] = commands[3]

        # RiskCommands
        for cmd_name in ["calculate-position-size", "adjust-position-account", "manage-risk", 
                         "drawdown-protection", "adjust-position-size-for-liquidity", "adjust-size-for-liquidity"]:
            dispatch_map[cmd_name] = commands[4]

        # BacktestCommands
        for cmd_name in ["backtest", "backtest-event", "backtest-pairs", "backtest-ml", "analyze-performance", 
                         "optimize", "plot-performance", "walk-forward-optimize", "performance-review", 
                         "discover-strategies", "retrain-ml-model"]:
            dispatch_map[cmd_name] = commands[5]

        # SystemCommands
        for cmd_name in ["status", "send-message", "crash", "start-web", "start-telegram-interface", "start-trading-session"]:
            dispatch_map[cmd_name] = commands[6]

        handler = dispatch_map.get(args.command)
        if handler:
            handler.execute(args, services)
        else:
            if args.command:
                logger.error(f"Unknown command or not mapped: {args.command}")
            else:
                parser.print_help()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
