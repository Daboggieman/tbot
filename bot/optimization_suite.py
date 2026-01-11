import logging
import itertools
import pandas as pd
from backtesting_engine import BacktestingEngine
from optimization_config import BEST_PARAMS

class OptimizationSuite:
    def __init__(self, strategy_class, historical_data, param_grid):
        self.strategy_class = strategy_class
        self.historical_data = historical_data
        self.param_grid = param_grid
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def run_optimization(self):
        self.logger.info(f"Running optimization for {self.strategy_class.__name__}...")
        
        results = []
        
        # Iterate over all combinations of parameters
        for params in self._generate_param_combinations(self.param_grid):
            self.logger.info(f"Testing parameters: {params}")
            
            # Instantiate the strategy with the current parameter set
            strategy = self.strategy_class(**params)
            
            # Run the backtest
            backtesting_engine = BacktestingEngine(strategy, self.historical_data)
            backtesting_engine.run_backtest()
            
            # Store the performance and parameters
            # The performance metrics are now calculated and logged by the backtesting engine itself.
            # We need a way to retrieve them. Let's assume the engine stores them.
            # For now, let's modify the backtesting engine to return the performance.
            # Let's assume run_backtest returns the sharpe ratio for now.
            # This part will require modification of the backtesting engine.
            # Let's assume for now that we can get the sharpe ratio.
            sharpe_ratio = backtesting_engine.sharpe_ratio # This is an assumption
            results.append({
                'params': params,
                'sharpe_ratio': sharpe_ratio
            })

        if not results:
            self.logger.warning("Optimization did not yield any results.")
            return None

        # Find the best parameters
        best_result = max(results, key=lambda x: x['sharpe_ratio'])
        best_params = best_result['params']
        best_performance = best_result['sharpe_ratio']

        self.logger.info("--- Optimization Results ---")
        self.logger.info(f"Best parameters found: {best_params}")
        self.logger.info(f"Best Sharpe Ratio: {best_performance:.2f}")
        self.logger.info("--------------------------")

        return best_params

    def run_walk_forward_optimization(self, strategy_name, window_size):
        """
        Runs walk-forward optimization on the most recent window of data.
        Updates the BEST_PARAMS with the optimized parameters for the strategy.
        """
        if len(self.historical_data) < window_size:
            self.logger.warning(f"Insufficient data for walk-forward optimization. Required: {window_size}, Available: {len(self.historical_data)}")
            return

        # Use the most recent window of data
        recent_data = self.historical_data.tail(window_size)

        # Create a new suite with the recent data
        walk_forward_suite = OptimizationSuite(self.strategy_class, recent_data, self.param_grid)

        # Run optimization
        best_params = walk_forward_suite.run_optimization()

        if best_params:
            # Update BEST_PARAMS
            BEST_PARAMS[strategy_name] = best_params
            self.logger.info(f"Updated BEST_PARAMS for {strategy_name}: {best_params}")
            # Persist the changes (since BEST_PARAMS is imported, we need to save to file)
            self._save_best_params()
        else:
            self.logger.warning(f"Walk-forward optimization failed for {strategy_name}")

    def _save_best_params(self):
        """Saves the BEST_PARAMS to the optimization_config.py file."""
        import os
        config_path = os.path.join(os.path.dirname(__file__), 'optimization_config.py')
        with open(config_path, 'r') as f:
            content = f.read()

        # Find the BEST_PARAMS block and replace it
        import re
        best_params_str = f"\n# Best parameters found from optimization, updated by walk-forward optimization\nBEST_PARAMS = {BEST_PARAMS}\n"
        pattern = r'# Best parameters found from optimization, updated by walk-forward optimization\nBEST_PARAMS = \{.*?\}\n'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, best_params_str, content, flags=re.DOTALL)
        else:
            # If not found, append at the end
            content += best_params_str

        with open(config_path, 'w') as f:
            f.write(content)

        self.logger.info("BEST_PARAMS saved to optimization_config.py")

    def _generate_param_combinations(self, param_grid):
        keys = param_grid.keys()
        values = param_grid.values()
        for instance in itertools.product(*values):
            yield dict(zip(keys, instance))