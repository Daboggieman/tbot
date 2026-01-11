import pandas as pd
from .utils import standardize_columns

class CCIStrategy:
    """
    A strategy based on the Commodity Channel Index (CCI).
    """
    def __init__(self, window=20, constant=0.015, buy_threshold=100, sell_threshold=-100):
        self.window = window
        self.constant = constant
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Typical Price
        tp = (data['High'] + data['Low'] + data['Close']) / 3

        # Calculate Simple Moving Average of Typical Price
        sma_tp = tp.rolling(window=self.window).mean()

        # Calculate Mean Deviation
        mean_deviation = abs(tp - sma_tp).rolling(window=self.window).mean()

        # Calculate CCI
        cci = (tp - sma_tp) / (self.constant * mean_deviation)

        # Generate signals
        signals.loc[cci < self.sell_threshold, 'signal'] = 1.0  # Buy when CCI is below sell_threshold (oversold)
        signals.loc[cci > self.buy_threshold, 'signal'] = -1.0 # Sell when CCI is above buy_threshold (overbought)

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
