import pandas as pd
import numpy as np
from .utils import standardize_columns

class OBVStrategy:
    """
    A strategy based on the On-Balance Volume (OBV) indicator.
    """
    def __init__(self):
        pass

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate OBV
        obv = (np.sign(data['Close'].diff()) * data['Volume']).fillna(0).cumsum()

        # Generate signals
        signals.loc[obv > obv.shift(1), 'signal'] = 1.0  # Buy when OBV is rising
        signals.loc[obv < obv.shift(1), 'signal'] = -1.0 # Sell when OBV is falling

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
