import pandas as pd
from .utils import standardize_columns

class MomentumStrategy:
    """
    A strategy based on the Momentum indicator.
    """
    def __init__(self, window=14):
        self.window = window

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Momentum
        momentum = data['Close'] - data['Close'].shift(self.window)

        # Generate signals
        signals.loc[momentum > 0, 'signal'] = 1.0  # Buy when momentum is positive
        signals.loc[momentum < 0, 'signal'] = -1.0 # Sell when momentum is negative

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
