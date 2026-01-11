import pandas as pd
import numpy as np
from .utils import standardize_columns

class MovingAverageCrossoverStrategy:
    """
    A simple moving average crossover strategy.
    """
    def __init__(self, short_window=40, long_window=100):
        """
        Initializes the MovingAverageCrossoverStrategy.

        Args:
            short_window (int): The short window for the moving average.
            long_window (int): The long window for the moving average.
        """
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data):
        """
        Generates trading signals for the given data.

        Args:
            data (pd.DataFrame): The historical market data.

        Returns:
            pd.DataFrame: A new DataFrame with 'signal' and 'positions' columns.
        """
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Create short simple moving average
        signals['short_mavg'] = data['Close'].rolling(window=self.short_window, min_periods=1, center=False).mean()

        # Create long simple moving average
        signals['long_mavg'] = data['Close'].rolling(window=self.long_window, min_periods=1, center=False).mean()

        # Create signals
        signals.loc[signals.index[self.short_window:], 'signal'] = np.where(signals['short_mavg'][self.short_window:] 
                                                                            > signals['long_mavg'][self.short_window:], 1.0, 0.0)

        # Generate trading events
        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
