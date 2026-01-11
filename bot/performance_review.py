import pandas as pd
import logging
from optimization_config import DISABLED_STRATEGIES

logger = logging.getLogger(__name__)

class PerformanceReviewer:
    def __init__(self, trades_filepath="trades.csv"):
        self.trades_filepath = trades_filepath

    def analyze_performance(self):
        """Analyze trading performance and identify underperforming strategies."""
        try:
            trades_df = pd.read_csv(self.trades_filepath)
        except FileNotFoundError:
            logger.warning(f"Trades file {self.trades_filepath} not found. Skipping performance review.")
            return

        if trades_df.empty:
            logger.info("No trades to analyze.")
            return

        # Calculate overall metrics
        total_pnl = trades_df['pnl'].sum()
        num_trades = len(trades_df)
        win_rate = (trades_df['pnl'] > 0).sum() / num_trades if num_trades > 0 else 0

        logger.info(f"Performance Review: Total PnL: {total_pnl:.4f}, Num Trades: {num_trades}, Win Rate: {win_rate:.2%}")

        # Analyze by hour of day
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        trades_df['hour'] = trades_df['date'].dt.hour
        hourly_pnl = trades_df.groupby('hour')['pnl'].sum()

        underperforming_hours = hourly_pnl[hourly_pnl < 0].index.tolist()
        logger.info(f"Underperforming hours: {underperforming_hours}")

        # Simple logic: if overall pnl negative and win rate < 50%, disable sentiment strategy as example
        if total_pnl < 0 and win_rate < 0.5:
            DISABLED_STRATEGIES.add('sentiment')
            logger.info("Disabled 'sentiment' strategy due to poor performance.")
            self._save_disabled_strategies()

    def _save_disabled_strategies(self):
        """Save disabled strategies to config file."""
        with open('optimization_config.py', 'r') as f:
            content = f.read()

        # Replace the DISABLED_STRATEGIES line
        import re
        new_disabled = f"DISABLED_STRATEGIES = {DISABLED_STRATEGIES}"
        content = re.sub(r'DISABLED_STRATEGIES = .*', new_disabled, content)

        with open('optimization_config.py', 'w') as f:
            f.write(content)

        logger.info("Disabled strategies saved to optimization_config.py")
