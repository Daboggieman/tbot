import pandas as pd
from .utils import standardize_columns

class KeltnerChannelsStrategy:
    """
    A strategy based on Keltner Channels.
    """
    def __init__(self, ema_window=20, atr_window=10, atr_multiplier=2.0):
        self.ema_window = ema_window
        self.atr_window = atr_window
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate EMA
        ema = data['Close'].ewm(span=self.ema_window, adjust=False).mean()

        # Calculate True Range (TR)
        tr1 = data['High'] - data['Low']
        tr2 = abs(data['High'] - data['Close'].shift(1))
        tr3 = abs(data['Low'] - data['Close'].shift(1))
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)

        # Calculate ATR
        atr = tr.ewm(span=self.atr_window, adjust=False).mean()

        # Calculate Keltner Channels
        upper_channel = ema + (self.atr_multiplier * atr)
        lower_channel = ema - (self.atr_multiplier * atr)

        # Generate signals
        signals.loc[data['Close'] > upper_channel, 'signal'] = 1.0  # Buy on breakout above upper channel
        signals.loc[data['Close'] < lower_channel, 'signal'] = -1.0 # Sell on breakout below lower channel

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
