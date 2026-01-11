import pandas as pd
from .utils import standardize_columns

class ROCStrategy:
    """
    A strategy based on the Price Rate of Change (ROC) indicator.
    """
    def __init__(self, window=12, buy_threshold=0, sell_threshold=0):
        self.window = window
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate ROC
        roc = ((data['Close'] - data['Close'].shift(self.window)) / data['Close'].shift(self.window)) * 100

        # Generate signals
        signals.loc[roc > self.buy_threshold, 'signal'] = 1.0  # Buy when ROC is above buy_threshold
        signals.loc[roc < self.sell_threshold, 'signal'] = -1.0 # Sell when ROC is below sell_threshold

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
