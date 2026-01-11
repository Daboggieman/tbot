import pandas as pd
import numpy as np
from .utils import standardize_columns

class SentimentAwareMovingAverageCrossoverStrategy:
    """
    A moving average crossover strategy that incorporates sentiment analysis.
    """
    def __init__(self, short_window=40, long_window=100, sentiment_threshold=0.1):
        """
        Initializes the SentimentAwareMovingAverageCrossoverStrategy.

        Args:
            short_window (int): The short window for the moving average.
            long_window (int): The long window for the moving average.
            sentiment_threshold (float): The sentiment threshold for generating signals.
        """
        self.short_window = short_window
        self.long_window = long_window
        self.sentiment_threshold = sentiment_threshold

    def generate_signals(self, data, sentiment_series):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Create short simple moving average
        signals['short_mavg'] = data['Close'].rolling(window=self.short_window, min_periods=1, center=False).mean()

        # Create long simple moving average
        signals['long_mavg'] = data['Close'].rolling(window=self.long_window, min_periods=1, center=False).mean()

        # Create signals based on moving average crossover
        signals['crossover_signal'] = np.where(signals['short_mavg'] > signals['long_mavg'], 1.0, -1.0)

        # Incorporate sentiment
        signals['sentiment'] = sentiment_series
        signals.loc[(signals['crossover_signal'] == 1.0) & (signals['sentiment'] > self.sentiment_threshold), 'signal'] = 1.0
        signals.loc[(signals['crossover_signal'] == -1.0) & (signals['sentiment'] < -self.sentiment_threshold), 'signal'] = -1.0

        # Generate trading events
        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
