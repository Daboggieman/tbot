import pandas as pd
import numpy as np
from .utils import standardize_columns

class IntermarketAwareMovingAverageCrossoverStrategy:
    """
    A moving average crossover strategy that incorporates intermarket analysis.
    """
    def __init__(self, short_window=40, long_window=100, correlation_window=20, correlation_threshold=0.5):
        """
        Initializes the IntermarketAwareMovingAverageCrossoverStrategy.

        Args:
            short_window (int): The short window for the moving average.
            long_window (int): The long window for the moving average.
            correlation_window (int): The window for calculating the correlation.
            correlation_threshold (float): The correlation threshold for generating signals.
        """
        self.short_window = short_window
        self.long_window = long_window
        self.correlation_window = correlation_window
        self.correlation_threshold = correlation_threshold

    def generate_signals(self, primary_data, secondary_data):
        primary_data = standardize_columns(primary_data)
        secondary_data = standardize_columns(secondary_data)
        signals = pd.DataFrame(index=primary_data.index)
        signals['signal'] = 0.0

        # Calculate moving averages for primary asset
        signals['short_mavg'] = primary_data['Close'].rolling(window=self.short_window, min_periods=1, center=False).mean()
        signals['long_mavg'] = primary_data['Close'].rolling(window=self.long_window, min_periods=1, center=False).mean()

        # Calculate correlation between primary and secondary assets
        correlation = primary_data['Close'].rolling(window=self.correlation_window).corr(secondary_data['Close'])
        signals['correlation'] = correlation

        # Generate signals
        # Buy if crossover AND positive correlation
        signals.loc[(signals['short_mavg'] > signals['long_mavg']) & (signals['correlation'] > self.correlation_threshold), 'signal'] = 1.0

        # Sell if crossover AND positive correlation (assuming we want to trade WITH the trend of the correlated asset)
        # If correlation is negative, we might want to do the opposite, but for this example we stick to positive correlation confirmation
        signals.loc[(signals['short_mavg'] < signals['long_mavg']) & (signals['correlation'] > self.correlation_threshold), 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
