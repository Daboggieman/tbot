import pandas as pd
from .utils import standardize_columns

class BollingerBandsSqueezeStrategy:
    """
    A strategy that identifies a Bollinger Bands squeeze and trades the breakout.
    """
    def __init__(self, window=20, num_std_dev=2, squeeze_threshold=2.33):
        self.window = window
        self.num_std_dev = num_std_dev
        self.squeeze_threshold = squeeze_threshold

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Bollinger Bands
        rolling_mean = data['Close'].rolling(window=self.window).mean()
        rolling_std = data['Close'].rolling(window=self.window).std()

        upper_band = rolling_mean + (rolling_std * self.num_std_dev)
        lower_band = rolling_mean - (rolling_std * self.num_std_dev)

        # Calculate Bollinger Bandwidth
        bandwidth = ((upper_band - lower_band) / rolling_mean) * 100
        
        # Identify squeeze
        squeeze = bandwidth < self.squeeze_threshold

        # Generate signals on breakout
        signals.loc[(squeeze.shift(1)) & (data['Close'] > upper_band), 'signal'] = 1.0  # Buy on breakout
        signals.loc[(squeeze.shift(1)) & (data['Close'] < lower_band), 'signal'] = -1.0 # Sell on breakout

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
