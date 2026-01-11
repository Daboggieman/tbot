import pandas as pd
from .utils import standardize_columns

class ATRBreakoutStrategy:
    """
    A strategy based on the Average True Range (ATR) breakout.
    """
    def __init__(self, atr_window=14, ma_window=20, atr_multiplier=2.0):
        self.atr_window = atr_window
        self.ma_window = ma_window
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate True Range (TR)
        tr1 = data['High'] - data['Low']
        tr2 = abs(data['High'] - data['Close'].shift(1))
        tr3 = abs(data['Low'] - data['Close'].shift(1))
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)

        # Calculate ATR
        atr = tr.ewm(span=self.atr_window, adjust=False).mean()

        # Calculate moving average
        ma = data['Close'].rolling(window=self.ma_window).mean()

        # Generate signals
        signals.loc[data['Close'] > ma + (self.atr_multiplier * atr), 'signal'] = 1.0  # Buy on breakout above ATR band
        signals.loc[data['Close'] < ma - (self.atr_multiplier * atr), 'signal'] = -1.0 # Sell on breakout below ATR band

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
