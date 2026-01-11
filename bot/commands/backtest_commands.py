from .base import BaseCommand
from historical_data_manager import HistoricalDataManager
from backtesting_engine import BacktestingEngine
from strategies import (
    MovingAverageCrossoverStrategy, RSIStrategy, MACDStrategy, BollingerBandsMeanReversionStrategy, 
    BollingerBandsSqueezeStrategy, DMIADXStrategy, ParabolicSARStrategy, IchimokuStrategy, 
    StochasticOscillatorStrategy, CCIStrategy, ROCStrategy, MomentumStrategy, ATRBreakoutStrategy, 
    KeltnerChannelsStrategy, OBVStrategy, VPTStrategy, ArbitrageStrategy, PairsTradingStrategy, 
    EventDrivenStrategy, IntermarketAwareMovingAverageCrossoverStrategy, WilliamsRStrategy, AroonStrategy
)

class BacktestCommands(BaseCommand):
    def add_arguments(self):
         # Backtest
        backtest_parser = self.parser.add_parser("backtest", help="Run a backtest of a trading strategy")
        backtest_parser.add_argument("strategy", type=str, help="The name of the strategy to backtest")
        backtest_parser.add_argument("symbol", type=str, help="The financial instrument to backtest on (e.g., EURUSD)")
        backtest_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        backtest_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
        backtest_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")
        backtest_parser.add_argument("--secondary-symbol", type=str, help="The secondary symbol for intermarket analysis")

        # Backtest Event-Driven
        backtest_event_parser = self.parser.add_parser("backtest-event", help="Run an event-driven backtest of a trading strategy")
        backtest_event_parser.add_argument("symbol", type=str, help="The financial instrument to backtest on (e.g., EURUSD)")
        backtest_event_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        backtest_event_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
        backtest_event_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")

        # Backtest Pairs
        backtest_pairs_parser = self.parser.add_parser("backtest-pairs", help="Run a backtest of a pairs trading strategy")
        backtest_pairs_parser.add_argument("strategy", type=str, help="The name of the pairs strategy to backtest (e.g., pairs_trading, arbitrage)")
        backtest_pairs_parser.add_argument("symbol_a", type=str, help="The first financial instrument in the pair")
        backtest_pairs_parser.add_argument("symbol_b", type=str, help="The second financial instrument in the pair")
        backtest_pairs_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        backtest_pairs_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
        backtest_pairs_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")

        # Backtest ML
        backtest_ml_parser = self.parser.add_parser("backtest-ml", help="Run a backtest of a machine learning strategy")
        backtest_ml_parser.add_argument("symbol", type=str, help="The financial instrument to backtest on (e.g., EURUSD)")
        backtest_ml_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        backtest_ml_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
        backtest_ml_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")

        # Performance Analytics
        self.parser.add_parser("analyze-performance", help="Run performance analytics on a set of trades")

        # Optimization
        optimization_parser = self.parser.add_parser("optimize", help="Run a strategy optimization")
        optimization_parser.add_argument("strategy", type=str, help="The name of the strategy to optimize")
        optimization_parser.add_argument("symbol", type=str, help="The financial instrument to optimize on (e.g., EURUSD)")
        optimization_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        optimization_parser.add_argument("start_date", type=str, help="The start date for the optimization in YYYY-MM-DD format")
        optimization_parser.add_argument("end_date", type=str, help="The end date for the optimization in YYYY-MM-DD format")

        # Plot Performance
        self.parser.add_parser("plot-performance", help="Plot the performance of a backtest from portfolio_history.csv")

        # Walk-Forward Optimize
        walk_forward_optimize_parser = self.parser.add_parser("walk-forward-optimize", help="Run walk-forward optimization to update strategy parameters")
        walk_forward_optimize_parser.add_argument("strategy", type=str, help="The name of the strategy to optimize")
        walk_forward_optimize_parser.add_argument("symbol", type=str, help="The financial instrument to optimize on (e.g., EURUSD)")
        walk_forward_optimize_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        walk_forward_optimize_parser.add_argument("window_days", type=int, help="The number of recent days to use for optimization")

        # Performance Review
        self.parser.add_parser("performance-review", help="Run automated performance review to disable underperforming strategies")

        # Discover Strategies
        discover_parser = self.parser.add_parser("discover-strategies", help="Run genetic algorithm to discover new trading strategies")
        discover_parser.add_argument("symbol", type=str, help="The financial instrument to use for discovery (e.g., EURUSD)")
        discover_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        discover_parser.add_argument("start_date", type=str, help="The start date for the backtest in YYYY-MM-DD format")
        discover_parser.add_argument("end_date", type=str, help="The end date for the backtest in YYYY-MM-DD format")
        discover_parser.add_argument("--population", type=int, default=50, help="Population size for GA")
        discover_parser.add_argument("--generations", type=int, default=20, help="Number of generations for GA")
        discover_parser.add_argument("--mutation_rate", type=float, default=0.1, help="Mutation rate for GA")
        discover_parser.add_argument("--crossover_rate", type=float, default=0.7, help="Crossover rate for GA")

        # Retrain ML Model
        retrain_parser = self.parser.add_parser("retrain-ml-model", help="Retrain the machine learning model on new data")
        retrain_parser.add_argument("symbol", type=str, help="The financial instrument to use for training (e.g., EURUSD)")
        retrain_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        retrain_parser.add_argument("start_date", type=str, help="The start date for the training data in YYYY-MM-DD format")
        retrain_parser.add_argument("end_date", type=str, help="The end date for the training data in YYYY-MM-DD format")


    def execute(self, args, services):
        order_manager = services.get('order_manager')
        
        if args.command == "backtest":
            self.logger.info(f"Executing backtest command for {args.symbol} with strategy {args.strategy}")
            historical_data_manager = HistoricalDataManager()
            data = historical_data_manager.load_data_from_csv(args.symbol, args.timeframe)
    
            if data is None:
                self.logger.error(f"Could not load historical data for {args.symbol} ({args.timeframe}). Please download it first.")
                return
    
            # Dynamic strategy loading
            import strategies
            # Create a map of lowercase names to classes
            strategy_map = {name.lower().replace('strategy', ''): cls for name, cls in vars(strategies).items() if isinstance(cls, type) and name.endswith('Strategy')}
            # Also add direct names
            strategy_map.update({name.lower(): cls for name, cls in vars(strategies).items() if isinstance(cls, type)})
            
            strategy_name = args.strategy.lower()
            strategy_class = strategy_map.get(strategy_name)
    
            if not strategy_class:
                self.logger.error(f"Unknown strategy: {args.strategy}. Available strategies: {', '.join(sorted(strategy_map.keys()))}")
                return

            # Check if multi-asset symbol is required (conceptual check)
            if strategy_name in ['arbitrage', 'pairs_trading', 'intermarket_aware_moving_average_crossover']:
                secondary_symbol = args.secondary_symbol or (args.symbol_b if 'symbol_b' in args else None)
                if not secondary_symbol:
                    self.logger.error(f"Strategy {args.strategy} requires a secondary symbol. Provide it with --secondary-symbol.")
                    return
                
                secondary_data = historical_data_manager.load_data_from_csv(secondary_symbol, args.timeframe)
                if secondary_data is None:
                    self.logger.error(f"Could not load historical data for secondary symbol {secondary_symbol}.")
                    return
                
                strategy = strategy_class()
                backtesting_engine = BacktestingEngine(strategy, data, historical_data_b=secondary_data)
                backtesting_engine.run_backtest()
            else:
                strategy = strategy_class()
                backtesting_engine = BacktestingEngine(strategy, data)
                backtesting_engine.run_backtest()

        elif args.command == "track-performance":
             self.logger.info("Executing track performance command")
             if order_manager:
                order_manager.track_performance()
