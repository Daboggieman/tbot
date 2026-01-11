import pandas as pd
from .utils import standardize_columns

class StochasticOscillatorStrategy:
    """
    A strategy based on the Stochastic Oscillator.
    """
    def __init__(self, k_window=14, d_window=3, buy_threshold=20, sell_threshold=80):
        self.k_window = k_window
        self.d_window = d_window
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate %K
        lowest_low = data['Low'].rolling(window=self.k_window).min()
        highest_high = data['High'].rolling(window=self.k_window).max()
        percent_k = ((data['Close'] - lowest_low) / (highest_high - lowest_low)) * 100

        # Calculate %D (3-period SMA of %K)
        percent_d = percent_k.rolling(window=self.d_window).mean()

        # Generate signals
        # Buy signal: %K crosses above %D and both are below buy_threshold
        signals.loc[(percent_k > percent_d) & (percent_k.shift(1) <= percent_d.shift(1)) & (percent_k < self.buy_threshold), 'signal'] = 1.0
        # Sell signal: %K crosses below %D and both are above sell_threshold
        signals.loc[(percent_k < percent_d) & (percent_k.shift(1) >= percent_d.shift(1)) & (percent_k > self.sell_threshold), 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
