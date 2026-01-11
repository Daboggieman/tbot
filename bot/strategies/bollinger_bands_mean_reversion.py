import pandas as pd
from .utils import standardize_columns

class BollingerBandsMeanReversionStrategy:
    """
    A strategy based on Bollinger Bands.
    """
    def __init__(self, window=20, num_std_dev=2):
        self.window = window
        self.num_std_dev = num_std_dev

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Bollinger Bands
        rolling_mean = data['Close'].rolling(window=self.window).mean()
        rolling_std = data['Close'].rolling(window=self.window).std()

        upper_band = rolling_mean + (rolling_std * self.num_std_dev)
        lower_band = rolling_mean - (rolling_std * self.num_std_dev)

        # Generate signals
        signals.loc[data['Close'] < lower_band, 'signal'] = 1.0  # Buy when price crosses below lower band
        signals.loc[data['Close'] > upper_band, 'signal'] = -1.0 # Sell when price crosses above upper band

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
