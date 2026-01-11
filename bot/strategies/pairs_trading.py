import pandas as pd
from .utils import standardize_columns

class PairsTradingStrategy:
    """
    A strategy that trades on the divergence and convergence of two correlated assets.
    """
    def __init__(self, window=20, threshold=1.5):
        self.window = window
        self.threshold = threshold

    def generate_signals(self, data_a, data_b):
        data_a = standardize_columns(data_a)
        data_b = standardize_columns(data_b)
        signals = pd.DataFrame(index=data_a.index)
        signals['signal_a'] = 0.0
        signals['signal_b'] = 0.0

        # Calculate the spread
        spread = data_a['Close'] - data_b['Close']

        # Calculate the moving average and standard deviation of the spread
        spread_mavg = spread.rolling(window=self.window).mean()
        spread_std = spread.rolling(window=self.window).std()

        # Calculate the z-score of the spread
        z_score = (spread - spread_mavg) / spread_std

        # Generate signals
        # Short the spread (short A, long B) when z-score is high
        signals.loc[z_score > self.threshold, 'signal_a'] = -1.0
        signals.loc[z_score > self.threshold, 'signal_b'] = 1.0

        # Long the spread (long A, short B) when z-score is low
        signals.loc[z_score < -self.threshold, 'signal_a'] = 1.0
        signals.loc[z_score < -self.threshold, 'signal_b'] = -1.0

        # Exit when the z-score crosses zero
        signals.loc[z_score.abs() < 0.5, 'signal_a'] = 0.0
        signals.loc[z_score.abs() < 0.5, 'signal_b'] = 0.0

        signals['positions_a'] = signals['signal_a'].diff()
        signals['positions_b'] = signals['signal_b'].diff()

        return signals[['signal_a', 'signal_b', 'positions_a', 'positions_b']]
