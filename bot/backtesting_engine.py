import logging
import pandas as pd
import numpy as np
from news_fetcher import NewsFetcher
from strategies import SentimentAwareMovingAverageCrossoverStrategy, IntermarketAwareMovingAverageCrossoverStrategy

class BacktestingEngine:
    def __init__(self, strategy, historical_data, historical_data_b=None, initial_capital=10000):
        """
        Initializes the BacktestingEngine.

        Args:
            strategy: The trading strategy to backtest.
            historical_data (pd.DataFrame): The historical market data for the first asset.
            historical_data_b (pd.DataFrame, optional): The historical market data for the second asset (for multi-asset strategies). Defaults to None.
            initial_capital (float): The initial capital for the backtest.
        """
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
        """Runs the backtest."""
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
        """Generates trading signals based on the strategy."""
        logging.info("Generating trading signals...")
        from strategies import ArbitrageStrategy, PairsTradingStrategy

        if isinstance(self.strategy, SentimentAwareMovingAverageCrossoverStrategy):
            symbol = self.historical_data.name if hasattr(self.historical_data, 'name') else 'EURUSD'
            start_date = self.historical_data.index.min().strftime('%Y-%m-%d')
            end_date = self.historical_data.index.max().strftime('%Y-%m-%d')
            
            news_fetcher = NewsFetcher()
            news_df = news_fetcher.fetch_news_and_analyze_sentiment(symbol, start_date, end_date)
            
            # Create a sentiment series with the same index as historical_data
            sentiment_series = pd.Series(index=self.historical_data.index, dtype=float).fillna(0.0)
            if news_df is not None and not news_df.empty:
                news_df['timestamp'] = pd.to_datetime(news_df['timestamp'])
                sentiment_series.update(news_df.set_index('timestamp')['sentiment'])
            
            self.signals = self.strategy.generate_signals(self.historical_data, sentiment_series)
        elif isinstance(self.strategy, (ArbitrageStrategy, PairsTradingStrategy)) and self.historical_data_b is not None:
            self.signals = self.strategy.generate_signals(self.historical_data, self.historical_data_b)
        elif isinstance(self.strategy, IntermarketAwareMovingAverageCrossoverStrategy) and self.historical_data_b is not None:
            self.signals = self.strategy.generate_signals(self.historical_data, self.historical_data_b)
        else:
            self.signals = self.strategy.generate_signals(self.historical_data)

    def _execute_trades(self):
        """Simulates the execution of trades based on the signals."""
        logging.info("Executing trades...")
        from strategies import ArbitrageStrategy, PairsTradingStrategy
        from machine_learning_strategy import MachineLearningStrategy
        if isinstance(self.strategy, (ArbitrageStrategy, PairsTradingStrategy)) and self.historical_data_b is not None:
            # Arbitrage strategy execution
            portfolio = pd.DataFrame(index=self.historical_data.index)
            
            # Ensure data is aligned
            data_b_aligned = self.historical_data_b.reindex(self.historical_data.index, method='ffill')

            # Calculate holdings for both assets
            holdings_a = (self.signals['signal_a'] * self.historical_data['Close']).cumsum()
            holdings_b = (self.signals['signal_b'] * data_b_aligned['Close']).cumsum()

            # Calculate cash changes from trades
            cash_a = (self.signals['signal_a'].diff() * self.historical_data['Close']).cumsum()
            cash_b = (self.signals['signal_b'].diff() * data_b_aligned['Close']).cumsum()

            portfolio['cash'] = self.initial_capital - (cash_a.fillna(0) + cash_b.fillna(0))
            portfolio['holdings'] = holdings_a + holdings_b
            portfolio['total'] = portfolio['cash'] + portfolio['holdings']
            portfolio['returns'] = portfolio['total'].pct_change()
            self.portfolio = portfolio

        else:
            # Single asset strategy execution
            symbol = self.historical_data.name if hasattr(self.historical_data, 'name') else 'asset'
            
            # Realign signals to historical data index
            self.signals = self.signals.reindex(self.historical_data.index, method='ffill')

            if isinstance(self.strategy, MachineLearningStrategy):
                # For ML strategies, the signal is the position
                self.positions[symbol] = self.signals['signal']
            else:
                # For other strategies, the signal triggers a position change
                self.positions[symbol] = self.signals['signal'].diff()

            # Drop NA values from positions
            self.positions.dropna(inplace=True)

            portfolio = pd.DataFrame(index=self.historical_data.index)
            portfolio['holdings'] = (self.positions[symbol] * self.historical_data['Close']).cumsum()
            portfolio['cash'] = self.initial_capital - (self.positions[symbol] * self.historical_data['Close']).cumsum()
            portfolio['total'] = portfolio['cash'] + portfolio['holdings']
            portfolio['returns'] = portfolio['total'].pct_change()
            self.portfolio = portfolio

            # Store trades
            positions = self.positions[symbol]
            for i in range(len(positions)):
                if positions.iloc[i] == 1 and (i == 0 or positions.iloc[i-1] != 1): # Buy
                    self.trades.append({'type': 'buy', 'date': positions.index[i], 'price': self.historical_data['Close'].loc[positions.index[i]], 'pnl': 0})
                elif positions.iloc[i] == -1 and (i == 0 or positions.iloc[i-1] != -1): # Sell
                    # Find the corresponding buy trade and update PnL
                    for trade in reversed(self.trades):
                        if trade['type'] == 'buy' and trade['pnl'] == 0:
                            pnl = self.historical_data['Close'].loc[positions.index[i]] - trade['price']
                            trade['pnl'] = pnl
                            self.trades.append({'type': 'sell', 'date': positions.index[i], 'price': self.historical_data['Close'].loc[positions.index[i]], 'pnl': pnl})
                            break


    def _calculate_performance(self):
        """Calculates and displays the performance of the strategy."""
        logging.info("Calculating performance...")
        
        total_return = (self.portfolio['total'].iloc[-1] / self.initial_capital) - 1
        
        # Handle case where standard deviation is zero
        if self.portfolio['returns'].std() == 0:
            sharpe_ratio = 0.0
        else:
            sharpe_ratio = np.sqrt(252) * (self.portfolio['returns'].mean() / self.portfolio['returns'].std())
        self.sharpe_ratio = sharpe_ratio
        
        # Calculate max drawdown
        rolling_max = self.portfolio['total'].cummax()
        daily_drawdown = self.portfolio['total']/rolling_max - 1.0
        max_drawdown = daily_drawdown.min()
        
        logging.info(f"Backtest Results:")
        logging.info(f"Total Return: {total_return:.2%}")
        logging.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        logging.info(f"Max Drawdown: {max_drawdown:.2%}")

    def run_event_driven_backtest(self):
        """Runs an event-driven backtest using both real price and real news data."""
        logging.info("Starting event-driven backtest with real news data...")
        from news_fetcher import NewsFetcher

        # 1. Fetch News Events
        symbol = self.historical_data.name if hasattr(self.historical_data, 'name') else 'EURUSD'
        start_date = self.historical_data.index.min().strftime('%Y-%m-%d')
        end_date = self.historical_data.index.max().strftime('%Y-%m-%d')
        
        news_fetcher = NewsFetcher()
        news_df = news_fetcher.fetch_news_and_analyze_sentiment(symbol, start_date, end_date)

        # 2. Prepare Price Events
        price_df = self.historical_data.copy()
        price_df['timestamp'] = price_df.index
        price_df['type'] = 'price'
        price_df['symbol'] = symbol

        # 3. Combine and Sort Events
        if news_df is not None and not news_df.empty:
            # Ensure timestamp columns are compatible
            news_df['timestamp'] = pd.to_datetime(news_df['timestamp'])
            price_df['timestamp'] = pd.to_datetime(price_df['timestamp'])
            
            combined_events = pd.concat([price_df, news_df], ignore_index=True)
            combined_events.sort_values(by='timestamp', inplace=True)
            combined_events.reset_index(drop=True, inplace=True)
        else:
            combined_events = price_df

        # 4. Initialize Portfolio
        self.portfolio = pd.DataFrame(index=self.historical_data.index, columns=['cash', 'holdings', 'total', 'returns'])
        self.portfolio.loc[self.portfolio.index[0], 'cash'] = self.initial_capital
        self.portfolio.loc[self.portfolio.index[0], 'holdings'] = 0
        self.portfolio.loc[self.portfolio.index[0], 'total'] = self.initial_capital
        self.portfolio.loc[self.portfolio.index[0], 'returns'] = 0
        position = 0
        entry_price = 0

        # 5. Process Event Stream
        for i in range(1, len(self.historical_data)):
            current_date = self.historical_data.index[i]
            events_for_day = combined_events[combined_events['timestamp'] == current_date]

            # Process all events for the current day
            for _, event in events_for_day.iterrows():
                signal = self.strategy.generate_signal(event.to_dict(), current_bar=i)
                
                if signal['signal'] == 'BUY' and position == 0:
                    position = 1
                    entry_price = self.historical_data.loc[current_date, 'Close']
                    self.trades.append({'type': 'buy', 'date': current_date, 'price': entry_price, 'pnl': 0})
                    self.portfolio.loc[current_date, 'cash'] = self.portfolio.iloc[i-1]['cash'] - entry_price
                elif signal['signal'] == 'SELL' and position == 1:
                    position = 0
                    exit_price = self.historical_data.loc[current_date, 'Close']
                    pnl = exit_price - entry_price
                    # Find the corresponding buy trade and update PnL
                    for trade in reversed(self.trades):
                        if trade['type'] == 'buy' and trade['pnl'] == 0:
                            trade['pnl'] = pnl
                            break
                    self.trades.append({'type': 'sell', 'date': current_date, 'price': exit_price, 'pnl': pnl})
                    self.portfolio.loc[current_date, 'cash'] = self.portfolio.iloc[i-1]['cash'] + exit_price

            # Update portfolio for the current day
            if not pd.isna(self.portfolio.loc[current_date, 'cash']):
                pass # Cash was updated by a trade
            else:
                self.portfolio.loc[current_date, 'cash'] = self.portfolio.iloc[i-1]['cash']

            self.portfolio.loc[current_date, 'holdings'] = position * self.historical_data.loc[current_date, 'Close']
            self.portfolio.loc[current_date, 'total'] = self.portfolio.loc[current_date, 'cash'] + self.portfolio.loc[current_date, 'holdings']
            self.portfolio.loc[current_date, 'returns'] = (self.portfolio.loc[current_date, 'total'] / self.portfolio.iloc[i-1]['total']) - 1

        self._calculate_performance()
        logging.info("Event-driven backtest finished.")
        self._save_portfolio_history_to_csv()

    def _save_trades_to_csv(self, filename="trades.csv"):
        """Saves the list of trades to a CSV file."""
        if not self.trades:
            logging.warning("No trades were made during the backtest. Nothing to save.")
            return

        trades_df = pd.DataFrame(self.trades)
        trades_df.to_csv(filename, index=False)
        logging.info(f"Trades saved to {filename}")

    def _save_portfolio_history_to_csv(self, filename="portfolio_history.csv"):
        """Saves the portfolio history to a CSV file."""
        if self.portfolio is None or self.portfolio.empty:
            logging.warning("Portfolio history is empty. Nothing to save.")
            return

        self.portfolio.to_csv(filename, index=True) # Save index (dates)
        logging.info(f"Portfolio history saved to {filename}")