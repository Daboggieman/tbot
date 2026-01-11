import pandas as pd
from .utils import standardize_columns

class DMIADXStrategy:
    """
    A strategy based on the Directional Movement Index (DMI) and Average Directional Index (ADX).
    """
    def __init__(self, window=14, adx_threshold=25):
        self.window = window
        self.adx_threshold = adx_threshold

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate True Range (TR)
        tr1 = data['High'] - data['Low']
        tr2 = abs(data['High'] - data['Close'].shift(1))
        tr3 = abs(data['Low'] - data['Close'].shift(1))
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)

        # Calculate Directional Movement (DM)
        plus_dm = data['High'] - data['High'].shift(1)
        minus_dm = data['Low'].shift(1) - data['Low']

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        plus_dm[plus_dm > minus_dm] = plus_dm
        plus_dm[plus_dm <= minus_dm] = 0

        minus_dm[minus_dm > plus_dm] = minus_dm
        minus_dm[minus_dm <= plus_dm] = 0

        # Calculate Smoothed True Range (ATR) and Directional Movement (ADX)
        atr = tr.ewm(span=self.window, adjust=False).mean()
        plus_di = (plus_dm.ewm(span=self.window, adjust=False).mean() / atr) * 100
        minus_di = (minus_dm.ewm(span=self.window, adjust=False).mean() / atr) * 100

        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.ewm(span=self.window, adjust=False).mean()

        # Generate signals
        # Buy signal: +DI crosses above -DI and ADX is above threshold
        signals.loc[(plus_di > minus_di) & (plus_di.shift(1) <= minus_di.shift(1)) & (adx > self.adx_threshold), 'signal'] = 1.0
        # Sell signal: -DI crosses above +DI and ADX is above threshold
        signals.loc[(minus_di > plus_di) & (minus_di.shift(1) <= plus_di.shift(1)) & (adx > self.adx_threshold), 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals[['signal', 'positions']]
