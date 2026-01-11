import pandas as pd
from .utils import standardize_columns

class MACDStrategy:
    """
    A strategy based on the Moving Average Convergence Divergence (MACD).
    """
    def __init__(self, fast_window=12, slow_window=26, signal_window=9):
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.signal_window = signal_window

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        exp1 = data['Close'].ewm(span=self.fast_window, adjust=False).mean()
        exp2 = data['Close'].ewm(span=self.slow_window, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=self.signal_window, adjust=False).mean()

        signals.loc[macd > signal, 'signal'] = 1.0
        signals.loc[macd < signal, 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
