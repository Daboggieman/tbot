import pandas as pd
from .utils import standardize_columns

class WilliamsRStrategy:
    """
    A strategy based on the Williams %R indicator.
    """
    def __init__(self, window=14, buy_threshold=-80, sell_threshold=-20):
        self.window = window
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Williams %R
        highest_high = data['High'].rolling(window=self.window).max()
        lowest_low = data['Low'].rolling(window=self.window).min()
        williams_r = ((highest_high - data['Close']) / (highest_high - lowest_low)) * -100

        # Generate signals
        # Buy when %R crosses above buy_threshold (oversold)
        signals.loc[(williams_r > self.buy_threshold) & (williams_r.shift(1) <= self.buy_threshold), 'signal'] = 1.0

        # Sell when %R crosses below sell_threshold (overbought)
        signals.loc[(williams_r < self.sell_threshold) & (williams_r.shift(1) >= self.sell_threshold), 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
