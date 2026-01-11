import pandas as pd
from .utils import standardize_columns

class RSIStrategy:
    """
    A strategy based on the Relative Strength Index (RSI).
    """
    def __init__(self, window=14, buy_threshold=30, sell_threshold=70, rsi_ma_window=5):
        self.window = window
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.rsi_ma_window = rsi_ma_window

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.window).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_ma = rsi.rolling(window=self.rsi_ma_window).mean()

        signals.loc[(rsi < self.buy_threshold) & (rsi > rsi_ma), 'signal'] = 1.0
        signals.loc[(rsi > self.sell_threshold) & (rsi < rsi_ma), 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
