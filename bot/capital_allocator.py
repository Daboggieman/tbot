import logging

class CapitalAllocator:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.strategy_performance = {} # {strategy_name: {'sharpe': 0.0, 'pnl': 0.0, 'trades': 0}}
        logging.info("CapitalAllocator initialized.")

    def update_strategy_performance(self, strategy_name, sharpe, pnl, trades):
        self.strategy_performance[strategy_name] = {
            'sharpe': sharpe,
            'pnl': pnl,
            'trades': trades
        }
        logging.info(f"Updated performance for {strategy_name}: Sharpe={sharpe:.2f}, PnL={pnl:.2f}, Trades={trades}")

    def get_allocation(self, strategy_name):
        # For now, a very simple allocation: equal if no performance data, otherwise based on Sharpe.
        if not self.strategy_performance:
            return 1.0 # Allocate 100% if no other strategies are tracked

        total_sharpe = sum(s['sharpe'] for s in self.strategy_performance.values() if s['sharpe'] > 0)
        
        if total_sharpe == 0:
            # If no profitable strategies, allocate equally
            return 1.0 / len(self.strategy_performance)
        
        strategy_data = self.strategy_performance.get(strategy_name)
        if strategy_data and strategy_data['sharpe'] > 0:
            return strategy_data['sharpe'] / total_sharpe
        else:
            return 0.0 # Allocate nothing to non-profitable strategies
