import pandas as pd
import logging
from .utils import standardize_columns

class IchimokuStrategy:
    """
    A strategy based on the Ichimoku Kinko Hyo indicator.
    """
    def __init__(self, tenkan_window=9, kijun_window=26, senkou_window=52):
        self.tenkan_window = tenkan_window
        self.kijun_window = kijun_window
        self.senkou_window = senkou_window

    def generate_signals(self, data):
        data = standardize_columns(data)
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        high_9 = data['High'].rolling(window=self.tenkan_window).max()
        low_9 = data['Low'].rolling(window=self.tenkan_window).min()
        tenkan_sen = (high_9 + low_9) / 2

        # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        high_26 = data['High'].rolling(window=self.kijun_window).max()
        low_26 = data['Low'].rolling(window=self.kijun_window).min()
        kijun_sen = (high_26 + low_26) / 2

        # Senkou Span A (Leading Span A): (Conversion Line + Base Line) / 2, plotted 26 periods ahead
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(self.kijun_window)

        # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, plotted 26 periods ahead
        high_52 = data['High'].rolling(window=self.senkou_window).max()
        low_52 = data['Low'].rolling(window=self.senkou_window).min()
        senkou_span_b = ((high_52 + low_52) / 2).shift(self.kijun_window)

        # Chikou Span (Lagging Span): Close plotted 26 periods behind
        chikou_span = data['Close'].shift(-self.kijun_window)

        # Generate signals
        # Buy signal: Tenkan-sen crosses above Kijun-sen
        signals.loc[(tenkan_sen > kijun_sen), 'signal'] = 1.0

        # Sell signal: Tenkan-sen crosses below Kijun-sen
        signals.loc[(tenkan_sen < kijun_sen), 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        # Debug logging
        logger = logging.getLogger(__name__)
        logger.info("--- Ichimoku Debug ---")
        logger.info(f"Tenkan-sen:\n{tenkan_sen.tail()}")
        logger.info(f"Kijun-sen:\n{kijun_sen.tail()}")
        logger.info(f"Signals:\n{signals.tail()}")
        logger.info("--- End Ichimoku Debug ---")

        return signals[['signal', 'positions']]
