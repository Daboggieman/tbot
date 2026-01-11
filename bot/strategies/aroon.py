import pandas as pd
from .utils import standardize_columns

class AroonStrategy:
    """
    A strategy based on the Aroon indicator.
    """
    def __init__(self, window=25):
        self.window = window

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Aroon Up and Aroon Down
        aroon_up = data['High'].rolling(window=self.window).apply(lambda x: x.argmax(), raw=True)
        aroon_up = ((self.window - aroon_up) / self.window) * 100

        aroon_down = data['Low'].rolling(window=self.window).apply(lambda x: x.argmin(), raw=True)
        aroon_down = ((self.window - aroon_down) / self.window) * 100

        # Generate signals
        # Buy when Aroon Up crosses above Aroon Down
        signals.loc[(aroon_up > aroon_down) & (aroon_up.shift(1) <= aroon_down.shift(1)), 'signal'] = 1.0

        # Sell when Aroon Down crosses above Aroon Up
        signals.loc[(aroon_down > aroon_up) & (aroon_down.shift(1) <= aroon_up.shift(1)), 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
