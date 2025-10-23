
import logging
import pandas as pd
import numpy as np
from news_fetcher import NewsFetcher
from strategies import SentimentAwareMovingAverageCrossoverStrategy, IntermarketAwareMovingAverageCrossoverStrategy

class BacktestingEngine:
    def __init__(self, strategy, historical_data, historical_data_b=None, initial_capital=10000):
        self.strategy = strategy
        self.historical_data = historical_data
        self.historical_data_b = historical_data_b
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = pd.DataFrame(index=historical_data.index).fillna(0.0)
        self.trades = []
        self.signals = None
        self.sharpe_ratio = 0
        logging.info("BacktestingEngine initialized.")

    def run_backtest(self):
        logging.info("Starting backtest...")
        from strategies import EventDrivenStrategy
        if isinstance(self.strategy, EventDrivenStrategy):
            self.run_event_driven_backtest()
        else:
            self._generate_signals()
            self._execute_trades()
            self._calculate_performance()
        
        self._save_trades_to_csv()
        self._save_portfolio_history_to_csv()
        logging.info("Backtest finished.")

    def _generate_signals(self):
        logging.info("Generating trading signals...")
        self.signals = self.strategy.generate_signals(self.historical_data)

    def _execute_trades(self):
        logging.info("Executing trades...")
        from machine_learning_strategy import MachineLearningStrategy

        symbol = self.historical_data.name if hasattr(self.historical_data, 'name') else 'asset'
        
        self.signals = self.signals.reindex(self.historical_data.index, method='ffill').fillna(0)

        if isinstance(self.strategy, MachineLearningStrategy):
            positions = self.signals['signal']
        else:
            positions = self.signals['signal'].diff().fillna(0)

        portfolio = pd.DataFrame(index=self.historical_data.index)
        portfolio['positions'] = positions.cumsum()
        portfolio['holdings'] = portfolio['positions'] * self.historical_data['Close']
        
        # Calculate cash changes from trades
        trades = positions * self.historical_data['Close']
        portfolio['cash'] = self.initial_capital - trades.cumsum()

        portfolio['total'] = portfolio['cash'] + portfolio['holdings']
        portfolio['returns'] = portfolio['total'].pct_change().fillna(0)
        self.portfolio = portfolio

        # Store trades for analysis
        for i in range(len(positions)):
            if positions.iloc[i] > 0: # Buy
                self.trades.append({'type': 'buy', 'date': positions.index[i], 'price': self.historical_data['Close'].iloc[i], 'pnl': 0})
            elif positions.iloc[i] < 0: # Sell
                # Find the corresponding buy trade and update PnL
                for trade in reversed(self.trades):
                    if trade['type'] == 'buy' and trade['pnl'] == 0:
                        pnl = self.historical_data['Close'].iloc[i] - trade['price']
                        trade['pnl'] = pnl
                        self.trades.append({'type': 'sell', 'date': positions.index[i], 'price': self.historical_data['Close'].iloc[i], 'pnl': pnl})
                        break

    def _calculate_performance(self):
        logging.info("Calculating performance...")
        
        if self.portfolio is None or self.portfolio.empty:
            self.sharpe_ratio = 0.0
            logging.warning("Portfolio is empty, cannot calculate performance.")
            return

        total_return = (self.portfolio['total'].iloc[-1] / self.initial_capital) - 1
        
        # Annualization factor
        # Assuming 252 trading days, 24 hours a day for H1 data
        annualization_factor = np.sqrt(252 * 24) 

        if self.portfolio['returns'].std() == 0:
            sharpe_ratio = 0.0
        else:
            sharpe_ratio = annualization_factor * (self.portfolio['returns'].mean() / self.portfolio['returns'].std())
        self.sharpe_ratio = sharpe_ratio
        
        rolling_max = self.portfolio['total'].cummax()
        daily_drawdown = self.portfolio['total']/rolling_max - 1.0
        max_drawdown = daily_drawdown.min()
        
        logging.info(f"Backtest Results:")
        logging.info(f"Total Return: {total_return:.2%}")
        logging.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        logging.info(f"Max Drawdown: {max_drawdown:.2%}")

    def run_event_driven_backtest(self):
        # This method is not used by the GA and is left as is.
        pass

    def _save_trades_to_csv(self, filename="trades.csv"):
        if not self.trades:
            logging.warning("No trades were made during the backtest. Nothing to save.")
            return

        trades_df = pd.DataFrame(self.trades)
        trades_df.to_csv(filename, index=False)
        logging.info(f"Trades saved to {filename}")

    def _save_portfolio_history_to_csv(self, filename="portfolio_history.csv"):
        if self.portfolio is None or self.portfolio.empty:
            logging.warning("Portfolio history is empty. Nothing to save.")
            return

        self.portfolio.to_csv(filename, index=True)
        logging.info(f"Portfolio history saved to {filename}")
