import pandas as pd
from .utils import standardize_columns

class VPTStrategy:
    """
    A strategy based on the Volume Price Trend (VPT) indicator.
    """
    def __init__(self, vpt_window=20):
        self.vpt_window = vpt_window

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate VPT
        vpt = (data['Volume'] * ((data['Close'] - data['Close'].shift(1)) / data['Close'].shift(1))).fillna(0).cumsum()

        # Calculate VPT moving average
        vpt_ma = vpt.rolling(window=self.vpt_window).mean()

        # Generate signals
        signals.loc[vpt > vpt_ma, 'signal'] = 1.0  # Buy when VPT is above its moving average
        signals.loc[vpt < vpt_ma, 'signal'] = -1.0 # Sell when VPT is below its moving average

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
