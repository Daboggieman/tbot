import pandas as pd
from .utils import standardize_columns

class ParabolicSARStrategy:
    """
    A strategy based on the Parabolic SAR indicator.
    """
    def __init__(self, af_start=0.02, af_increment=0.02, af_max=0.2):
        self.af_start = af_start
        self.af_increment = af_increment
        self.af_max = af_max

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Initialize SAR values
        sar = data['Close'].copy()
        ep = data['Close'].copy() # Extreme Point
        af = self.af_start # Acceleration Factor
        long_trend = True # True if in a long trend, False if in a short trend

        for i in range(1, len(data)):
            if long_trend:
                sar.iloc[i] = sar.iloc[i-1] + af * (ep.iloc[i-1] - sar.iloc[i-1])
                if data['Low'].iloc[i] < sar.iloc[i]: # Trend reversal
                    long_trend = False
                    sar.iloc[i] = ep.iloc[i-1] # SAR becomes previous EP
                    af = self.af_start
                    ep.iloc[i] = data['Low'].iloc[i] # New EP is current Low
                    signals.loc[data.index[i], 'signal'] = -1.0 # Sell signal
                else:
                    if data['High'].iloc[i] > ep.iloc[i-1]:
                        ep.iloc[i] = data['High'].iloc[i]
                        af = min(af + self.af_increment, self.af_max)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                    signals.loc[data.index[i], 'signal'] = 1.0 # Hold long
            else: # Short trend
                sar.iloc[i] = sar.iloc[i-1] - af * (sar.iloc[i-1] - ep.iloc[i-1])
                if data['High'].iloc[i] > sar.iloc[i]: # Trend reversal
                    long_trend = True
                    sar.iloc[i] = ep.iloc[i-1] # SAR becomes previous EP
                    af = self.af_start
                    ep.iloc[i] = data['High'].iloc[i] # New EP is current High
                    signals.loc[data.index[i], 'signal'] = 1.0 # Buy signal
                else:
                    if data['Low'].iloc[i] < ep.iloc[i-1]:
                        ep.iloc[i] = data['Low'].iloc[i]
                        af = min(af + self.af_increment, self.af_max)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                    signals.loc[data.index[i], 'signal'] = -1.0 # Hold short

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
