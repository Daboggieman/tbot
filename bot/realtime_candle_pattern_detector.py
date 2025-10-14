import pandas as pd
from collections import deque

class RealtimeCandlePatternDetector:
    """
    Detects candlestick patterns on a rolling window of candle data in real-time.
    """
    def __init__(self, pattern_window=5, body_size_threshold=0.001):
        """
        Initializes the RealtimeCandlePatternDetector.

        Args:
            pattern_window (int): The number of recent candles to keep for pattern detection.
            body_size_threshold (float): A threshold to determine if a candle body is small (e.g., for a Doji).
        """
        self.data = deque(maxlen=pattern_window)
        self.body_size_threshold = body_size_threshold
        self.patterns = [
            # Single Candle Patterns
            'doji', 'hammer', 'inverted_hammer', 'hanging_man', 'shooting_star',
            # Two Candle Patterns
            'bullish_engulfing', 'bearish_engulfing', 'tweezer_top', 'tweezer_bottom',
            # Three Candle Patterns
            'morning_star', 'evening_star', 'three_white_soldiers', 'three_black_crows'
        ]
        self.pattern_types = {
            'doji': 'reversal',
            'hammer': 'reversal',
            'inverted_hammer': 'reversal',
            'hanging_man': 'reversal',
            'shooting_star': 'reversal',
            'bullish_engulfing': 'bullish',
            'bearish_engulfing': 'bearish',
            'tweezer_top': 'reversal',
            'tweezer_bottom': 'reversal',
            'morning_star': 'reversal',
            'evening_star': 'reversal',
            'three_white_soldiers': 'bullish',
            'three_black_crows': 'bearish'
        }

    def add_candle(self, candle):
        """
        Adds a new candle to the internal data window.

        Args:
            candle (dict): A dictionary representing a single candle with keys
                           {'Timestamp', 'Open', 'High', 'Low', 'Close'}.
        """
        self.data.append(candle)

    def detect_at_latest_candle(self):
        """
        Runs all pattern detection logic on the most recent candle available.

        Returns:
            list: A list of dictionaries, where each dict contains a detected pattern's name and type.
                  e.g., [{'name': 'Doji', 'type': 'reversal'}]
        """
        if len(self.data) == 0:
            return []

        df = pd.DataFrame(list(self.data))
        df.set_index('Timestamp', inplace=True)

        detected_patterns = []
        latest_index = len(df) - 1

        for pattern_name in self.patterns:
            pattern_func = getattr(self, f'_is_{pattern_name}', None)
            if pattern_func and pattern_func(df, latest_index):
                detected_patterns.append({
                    'name': pattern_name.replace('_', ' ').title(),
                    'type': self.pattern_types.get(pattern_name, 'unknown')
                })

        return detected_patterns

    # Helper methods adapted to take a DataFrame and index
    def _is_bullish(self, df, i):
        return df['Close'].iloc[i] > df['Open'].iloc[i]

    def _is_bearish(self, df, i):
        return df['Close'].iloc[i] < df['Open'].iloc[i]

    def _body(self, df, i):
        return abs(df['Close'].iloc[i] - df['Open'].iloc[i])

    def _upper_shadow(self, df, i):
        if self._is_bullish(df, i):
            return df['High'].iloc[i] - df['Close'].iloc[i]
        else:
            return df['High'].iloc[i] - df['Open'].iloc[i]

    def _lower_shadow(self, df, i):
        if self._is_bullish(df, i):
            return df['Open'].iloc[i] - df['Low'].iloc[i]
        else:
            return df['Close'].iloc[i] - df['Low'].iloc[i]
    
    def _real_body_center(self, df, i):
        return (df['Open'].iloc[i] + df['Close'].iloc[i]) / 2

    # Single Candle Patterns
    def _is_doji(self, df, i):
        return self._body(df, i) <= self.body_size_threshold

    def _is_hammer(self, df, i):
        if i < 1: return False
        # Downtrend check (simple version: previous candle is bearish)
        if not self._is_bearish(df, i-1): return False
        body = self._body(df, i)
        if body == 0: return False
        return self._lower_shadow(df, i) > 2 * body and self._upper_shadow(df, i) < body * 0.5

    def _is_inverted_hammer(self, df, i):
        if i < 1: return False
        if not self._is_bearish(df, i-1): return False
        body = self._body(df, i)
        if body == 0: return False
        return self._upper_shadow(df, i) > 2 * body and self._lower_shadow(df, i) < body * 0.5

    def _is_hanging_man(self, df, i):
        if i < 1: return False
        # Uptrend check (simple version: previous candle is bullish)
        if not self._is_bullish(df, i-1): return False
        body = self._body(df, i)
        if body == 0: return False
        return self._lower_shadow(df, i) > 2 * body and self._upper_shadow(df, i) < body * 0.5

    def _is_shooting_star(self, df, i):
        if i < 1: return False
        if not self._is_bullish(df, i-1): return False
        body = self._body(df, i)
        if body == 0: return False
        return self._upper_shadow(df, i) > 2 * body and self._lower_shadow(df, i) < body * 0.5

    # Two Candle Patterns
    def _is_bullish_engulfing(self, df, i):
        if i < 1: return False
        return self._is_bearish(df, i-1) and self._is_bullish(df, i) and \
               df['Close'].iloc[i] > df['Open'].iloc[i-1] and \
               df['Open'].iloc[i] < df['Close'].iloc[i-1]

    def _is_bearish_engulfing(self, df, i):
        if i < 1: return False
        return self._is_bullish(df, i-1) and self._is_bearish(df, i) and \
               df['Open'].iloc[i] > df['Close'].iloc[i-1] and \
               df['Close'].iloc[i] < df['Open'].iloc[i-1]

    def _is_tweezer_top(self, df, i):
        if i < 1: return False
        if not (self._is_bullish(df, i-1) and self._is_bearish(df, i)): return False
        return abs(df['High'].iloc[i-1] - df['High'].iloc[i]) < self.body_size_threshold

    def _is_tweezer_bottom(self, df, i):
        if i < 1: return False
        if not (self._is_bearish(df, i-1) and self._is_bullish(df, i)): return False
        return abs(df['Low'].iloc[i-1] - df['Low'].iloc[i]) < self.body_size_threshold

    # Three Candle Patterns
    def _is_morning_star(self, df, i):
        if i < 2: return False
        if not (self._is_bearish(df, i-2) and self._body(df, i-2) > self.body_size_threshold * 3): return False
        if not (self._body(df, i-1) < self.body_size_threshold and df['Open'].iloc[i-1] < df['Close'].iloc[i-2]): return False
        return self._is_bullish(df, i) and df['Close'].iloc[i] > self._real_body_center(df, i-2)

    def _is_evening_star(self, df, i):
        if i < 2: return False
        if not (self._is_bullish(df, i-2) and self._body(df, i-2) > self.body_size_threshold * 3): return False
        if not (self._body(df, i-1) < self.body_size_threshold and df['Open'].iloc[i-1] > df['Close'].iloc[i-2]): return False
        return self._is_bearish(df, i) and df['Close'].iloc[i] < self._real_body_center(df, i-2)

    def _is_three_white_soldiers(self, df, i):
        if i < 2: return False
        if not (self._is_bullish(df, i) and self._is_bullish(df, i-1) and self._is_bullish(df, i-2)): return False
        if not (self._body(df, i) > self.body_size_threshold * 2 and self._body(df, i-1) > self.body_size_threshold * 2 and self._body(df, i-2) > self.body_size_threshold * 2): return False
        if not (df['Open'].iloc[i] > df['Open'].iloc[i-1] and df['Open'].iloc[i-1] > df['Open'].iloc[i-2]): return False
        return df['Close'].iloc[i] > df['Close'].iloc[i-1] and df['Close'].iloc[i-1] > df['Close'].iloc[i-2]

    def _is_three_black_crows(self, df, i):
        if i < 2: return False
        if not (self._is_bearish(df, i) and self._is_bearish(df, i-1) and self._is_bearish(df, i-2)): return False
        if not (self._body(df, i) > self.body_size_threshold * 2 and self._body(df, i-1) > self.body_size_threshold * 2 and self._body(df, i-2) > self.body_size_threshold * 2): return False
        if not (df['Open'].iloc[i] < df['Open'].iloc[i-1] and df['Open'].iloc[i-1] < df['Open'].iloc[i-2]): return False
        return df['Close'].iloc[i] < df['Close'].iloc[i-1] and df['Close'].iloc[i-1] < df['Close'].iloc[i-2]