import pandas as pd
from .utils import standardize_columns

class ArbitrageStrategy:
    """
    A conceptual strategy for identifying arbitrage opportunities between two data sources.
    """
    def __init__(self, threshold=0.001):
        self.threshold = threshold

    def generate_signals(self, data_a, data_b):
        data_a = standardize_columns(data_a)
        data_b = standardize_columns(data_b)
        signals = pd.DataFrame(index=data_a.index)
        signals['signal_a'] = 0.0
        signals['signal_b'] = 0.0

        # Calculate price difference
        price_diff = data_a['Close'] - data_b['Close']

        # Generate signals
        signals.loc[price_diff > self.threshold, 'signal_a'] = -1.0 # Sell on source A
        signals.loc[price_diff > self.threshold, 'signal_b'] = 1.0  # Buy on source B

        signals.loc[price_diff < -self.threshold, 'signal_a'] = 1.0  # Buy on source A
        signals.loc[price_diff < -self.threshold, 'signal_b'] = -1.0 # Sell on source B

        signals['positions_a'] = signals['signal_a'].diff()
        signals['positions_b'] = signals['signal_b'].diff()

        return signals[['signal_a', 'signal_b', 'positions_a', 'positions_b']]
