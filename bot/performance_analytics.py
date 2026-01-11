import logging
import pandas as pd
import os

class PerformanceAnalytics:
    def __init__(self, trades_filepath="trades.csv"):
        self.trades_filepath = trades_filepath
        self.trades = self._load_trades()
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _load_trades(self):
        """Loads trades from the specified CSV file."""
        if not os.path.exists(self.trades_filepath):
            self.logger.warning(f"Trades file not found at: {self.trades_filepath}")
            return None
        try:
            return pd.read_csv(self.trades_filepath)
        except Exception as e:
            self.logger.error(f"Error loading trades file: {e}")
            return None

    def run(self):
        """Runs the performance analytics calculations and prints the results."""
        self.logger.info("Running performance analytics...")
        if self.trades is None or self.trades.empty:
            self.logger.warning("No trades to analyze.")
            return

        # Filter out only the sell trades for PnL analysis
        sell_trades = self.trades[self.trades['type'] == 'sell'].copy()

        if sell_trades.empty:
            self.logger.warning("No completed trades (sell orders) to analyze.")
            return

        total_trades = len(sell_trades)
        win_loss_ratio = self._calculate_win_loss_ratio(sell_trades)
        avg_profit, avg_loss = self._calculate_average_profit_loss(sell_trades)
        profit_factor = self._calculate_profit_factor(sell_trades)

        self.logger.info("--- Trade Performance Analytics ---")
        self.logger.info(f"Total Completed Trades: {total_trades}")
        self.logger.info(f"Win/Loss Ratio: {win_loss_ratio:.2f}")
        self.logger.info(f"Average Profit: {avg_profit:.2f}")
        self.logger.info(f"Average Loss: {avg_loss:.2f}")
        self.logger.info(f"Profit Factor: {profit_factor:.2f}")
        self.logger.info("-----------------------------------")

    def _calculate_win_loss_ratio(self, trades_df):
        """Calculates the win/loss ratio."""
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] < 0]
        if len(losses) == 0:
            return float('inf') # Avoid division by zero if there are no losses
        return len(wins) / len(losses)

    def _calculate_average_profit_loss(self, trades_df):
        """Calculates the average profit and average loss."""
        wins = trades_df[trades_df['pnl'] > 0]['pnl']
        losses = trades_df[trades_df['pnl'] < 0]['pnl']
        
        avg_profit = wins.mean() if not wins.empty else 0
        avg_loss = losses.mean() if not losses.empty else 0
        
        return avg_profit, avg_loss

    def _calculate_profit_factor(self, trades_df):
        """Calculates the profit factor."""
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        
        if gross_loss == 0:
            return float('inf') # Avoid division by zero if there are no losses
            
        return gross_profit / gross_loss