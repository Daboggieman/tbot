import pandas as pd

class CandlePatternDetector:
    def __init__(self, data, body_size_threshold=0.001):
        self.data = data
        self.body_size_threshold = body_size_threshold
        self.patterns = [
            # Single Candle Patterns
            'doji', 'long_legged_doji', 'dragonfly_doji', 'gravestone_doji',
            'spinning_top', 'high_wave',
            'hammer', 'inverted_hammer', 'hanging_man', 'shooting_star',
            'long_white_candlestick', 'long_black_candlestick',
            'marubozu_white', 'marubozu_black',
            'bullish_belt_hold', 'bearish_belt_hold',

            # Two Candle Patterns
            'bullish_engulfing', 'bearish_engulfing',
            'piercing_line', 'dark_cloud_cover',
            'tweezer_top', 'tweezer_bottom',
            'bullish_harami', 'bearish_harami',
            'bullish_doji_star', 'bearish_doji_star',
            'bullish_meeting_lines', 'bearish_meeting_lines',
            'bullish_separating_lines', 'bearish_separating_lines',
            'bullish_kicking', 'bearish_kicking',
            'homing_pigeon', 'matching_low',
            'counterattack_lines', 'hook_reversal',

            # Three Candle Patterns
            'morning_star', 'evening_star',
            'three_white_soldiers', 'three_black_crows',
            'three_inside_up', 'three_inside_down',
            'three_outside_up', 'three_outside_down',
            'abandoned_baby_bullish', 'abandoned_baby_bearish',
            'three_stars_in_the_south', 'three_stars_in_the_north',
            'concealing_baby_swallow', 'deliberation',
            'identical_three_crows', 'unique_three_river_bottom',
            'advance_block', 'stalled_pattern',
            'upside_gap_two_crows',
            'rising_window', 'falling_window',
            'stick_sandwich',
            'rising_three_methods', 'falling_three_methods',
            'on_neck_line', 'in_neck_line', 'thrusting_line',
            'downside_gap_three_methods', 'ladder_bottom', 'breakaway',
            'side_by_side_white_lines_bullish', 'side_by_side_white_lines_bearish',
            'tasuki_gap_up'
        ]

    def detect(self):
        """Detects all implemented candlestick patterns in the data."""
        results = {}
        for i in range(len(self.data)):
            for pattern_name in self.patterns:
                # The pattern function name is assumed to be '_is_' + pattern_name
                pattern_func = getattr(self, f'_is_{pattern_name}', None)
                if pattern_func and pattern_func(i):
                    date = self.data.index[i]
                    if date not in results:
                        results[date] = []
                    results[date].append(pattern_name.replace('_', ' ').title())
        return results

    # Helper methods
    def _is_bullish(self, i):
        return self.data['Close'].iloc[i] > self.data['Open'].iloc[i]

    def _is_bearish(self, i):
        return self.data['Close'].iloc[i] < self.data['Open'].iloc[i]

    def _body(self, i):
        return abs(self.data['Close'].iloc[i] - self.data['Open'].iloc[i])

    def _upper_shadow(self, i):
        if self._is_bullish(i):
            return self.data['High'].iloc[i] - self.data['Close'].iloc[i]
        else:
            return self.data['High'].iloc[i] - self.data['Open'].iloc[i]

    def _lower_shadow(self, i):
        if self._is_bullish(i):
            return self.data['Open'].iloc[i] - self.data['Low'].iloc[i]
        else:
            return self.data['Close'].iloc[i] - self.data['Low'].iloc[i]

    def _real_body_center(self, i):
        return (self.data['Open'].iloc[i] + self.data['Close'].iloc[i]) / 2

    def _is_gap_up(self, i):
        if i == 0: return False
        return self.data['Low'].iloc[i] > self.data['High'].iloc[i-1]

    def _is_gap_down(self, i):
        if i == 0: return False
        return self.data['High'].iloc[i] < self.data['Low'].iloc[i-1]

    # Single Candle Patterns
    def _is_doji(self, i):
        return self._body(i) <= self.body_size_threshold

    def _is_long_legged_doji(self, i):
        return self._is_doji(i) and self._upper_shadow(i) > self._body(i) * 3 and self._lower_shadow(i) > self._body(i) * 3

    def _is_dragonfly_doji(self, i):
        return self._is_doji(i) and self._lower_shadow(i) > self._body(i) * 3 and self._upper_shadow(i) < self._body(i) * 0.1

    def _is_gravestone_doji(self, i):
        return self._is_doji(i) and self._upper_shadow(i) > self._body(i) * 3 and self._lower_shadow(i) < self._body(i) * 0.1

    def _is_spinning_top(self, i):
        body = self._body(i)
        if body == 0: return False # Avoid division by zero for doji
        return self._upper_shadow(i) > body and self._lower_shadow(i) > body

    def _is_high_wave(self, i):
        return self._upper_shadow(i) > self._body(i) * 2 and self._lower_shadow(i) > self._body(i) * 2

    def _is_hammer(self, i):
        if i == 0: return False
        # Downtrend check
        if not (self.data['Close'].iloc[i-1] < self.data['Open'].iloc[i-1]):
            return False
        body = self._body(i)
        if body == 0: return False
        return self._lower_shadow(i) > 2 * body and self._upper_shadow(i) < body * 0.5

    def _is_inverted_hammer(self, i):
        if i == 0: return False
        # Downtrend check
        if not (self.data['Close'].iloc[i-1] < self.data['Open'].iloc[i-1]):
            return False
        body = self._body(i)
        if body == 0: return False
        return self._upper_shadow(i) > 2 * body and self._lower_shadow(i) < body * 0.5

    def _is_hanging_man(self, i):
        if i == 0: return False
        # Uptrend check
        if not (self.data['Close'].iloc[i-1] > self.data['Open'].iloc[i-1]):
            return False
        body = self._body(i)
        if body == 0: return False
        return self._lower_shadow(i) > 2 * body and self._upper_shadow(i) < body * 0.5

    def _is_shooting_star(self, i):
        if i == 0: return False
        # Uptrend check
        if not (self.data['Close'].iloc[i-1] > self.data['Open'].iloc[i-1]):
            return False
        body = self._body(i)
        if body == 0: return False
        return self._upper_shadow(i) > 2 * body and self._lower_shadow(i) < body * 0.5

    def _is_long_white_candlestick(self, i):
        return self._is_bullish(i) and self._body(i) > self.data['Open'].iloc[i] * 0.03 # 3% of opening price

    def _is_long_black_candlestick(self, i):
        return self._is_bearish(i) and self._body(i) > self.data['Open'].iloc[i] * 0.03 # 3% of opening price

    def _is_marubozu_white(self, i):
        return self._is_bullish(i) and self._upper_shadow(i) < self.body_size_threshold and self._lower_shadow(i) < self.body_size_threshold

    def _is_marubozu_black(self, i):
        return self._is_bearish(i) and self._upper_shadow(i) < self.body_size_threshold and self._lower_shadow(i) < self.body_size_threshold

    def _is_bullish_belt_hold(self, i):
        if i == 0: return False
        # Downtrend check
        if not self._is_bearish(i-1): return False
        # Opens at or near the low, and is a long white candle
        return self._is_bullish(i) and self._lower_shadow(i) < self.body_size_threshold and self._body(i) > self.data['Open'].iloc[i] * 0.02

    def _is_bearish_belt_hold(self, i):
        if i == 0: return False
        # Uptrend check
        if not self._is_bullish(i-1): return False
        # Opens at or near the high, and is a long black candle
        return self._is_bearish(i) and self._upper_shadow(i) < self.body_size_threshold and self._body(i) > self.data['Open'].iloc[i] * 0.02

    # Two Candle Patterns
    def _is_bullish_engulfing(self, i):
        if i == 0: return False
        return self._is_bearish(i-1) and self._is_bullish(i) and \
               self.data['Close'].iloc[i] > self.data['Open'].iloc[i-1] and \
               self.data['Open'].iloc[i] < self.data['Close'].iloc[i-1]

    def _is_bearish_engulfing(self, i):
        if i == 0: return False
        return self._is_bullish(i-1) and self._is_bearish(i) and \
               self.data['Open'].iloc[i] > self.data['Close'].iloc[i-1] and \
               self.data['Close'].iloc[i] < self.data['Open'].iloc[i-1]

    def _is_piercing_line(self, i):
        if i == 0: return False
        # Previous day is bearish
        if not self._is_bearish(i-1): return False
        # Current day is bullish
        if not self._is_bullish(i): return False
        # Current day opens below previous day's low
        if not self.data['Open'].iloc[i] < self.data['Low'].iloc[i-1]: return False
        # Current day closes above 50% of previous day's body
        if not self.data['Close'].iloc[i] > self._real_body_center(i-1): return False
        # Current day does not close above previous day's open
        if not self.data['Close'].iloc[i] < self.data['Open'].iloc[i-1]: return False
        return True

    def _is_dark_cloud_cover(self, i):
        if i == 0: return False
        # Previous day is bullish
        if not self._is_bullish(i-1): return False
        # Current day is bearish
        if not self._is_bearish(i): return False
        # Current day opens above previous day's high
        if not self.data['Open'].iloc[i] > self.data['High'].iloc[i-1]: return False
        # Current day closes below 50% of previous day's body
        if not self.data['Close'].iloc[i] < self._real_body_center(i-1): return False
        # Current day does not close below previous day's open
        if not self.data['Close'].iloc[i] > self.data['Open'].iloc[i-1]: return False
        return True

    def _is_tweezer_top(self, i):
        if i == 0: return False
        # First candle is bullish, second is bearish
        if not (self._is_bullish(i-1) and self._is_bearish(i)): return False
        # Highs are nearly the same
        return abs(self.data['High'].iloc[i-1] - self.data['High'].iloc[i]) < self.body_size_threshold

    def _is_tweezer_bottom(self, i):
        if i == 0: return False
        # First candle is bearish, second is bullish
        if not (self._is_bearish(i-1) and self._is_bullish(i)): return False
        # Lows are nearly the same
        return abs(self.data['Low'].iloc[i-1] - self.data['Low'].iloc[i]) < self.body_size_threshold

    def _is_bullish_harami(self, i):
        if i == 0: return False
        # Previous day is long and bearish
        if not (self._is_bearish(i-1) and self._body(i-1) > self.body_size_threshold * 3): return False
        # Current day is bullish and contained within the previous day's body
        return self._is_bullish(i) and \
               self.data['Open'].iloc[i] > self.data['Close'].iloc[i-1] and \
               self.data['Close'].iloc[i] < self.data['Open'].iloc[i-1]

    def _is_bearish_harami(self, i):
        if i == 0: return False
        # Previous day is long and bullish
        if not (self._is_bullish(i-1) and self._body(i-1) > self.body_size_threshold * 3): return False
        # Current day is bearish and contained within the previous day's body
        return self._is_bearish(i) and \
               self.data['Open'].iloc[i] < self.data['Close'].iloc[i-1] and \
               self.data['Close'].iloc[i] > self.data['Open'].iloc[i-1]

    def _is_bullish_doji_star(self, i):
        if i < 1: return False
        # A long bearish candle followed by a doji that gapped down
        return self._is_bearish(i-1) and self._body(i-1) > self.body_size_threshold * 3 and \
               self._is_doji(i) and self.data['Open'].iloc[i] < self.data['Close'].iloc[i-1]

    def _is_bearish_doji_star(self, i):
        if i < 1: return False
        # A long bullish candle followed by a doji that gapped up
        return self._is_bullish(i-1) and self._body(i-1) > self.body_size_threshold * 3 and \
               self._is_doji(i) and self.data['Open'].iloc[i] > self.data['Close'].iloc[i-1]

    def _is_bullish_meeting_lines(self, i):
        if i < 1: return False
        # A long bearish candle followed by a long bullish candle
        # with a similar closing price.
        return self._is_bearish(i-1) and self._is_bullish(i) and \
               self._body(i-1) > self.body_size_threshold * 3 and \
               self._body(i) > self.body_size_threshold * 3 and \
               abs(self.data['Close'].iloc[i-1] - self.data['Close'].iloc[i]) < self.body_size_threshold

    def _is_bearish_meeting_lines(self, i):
        if i < 1: return False
        # A long bullish candle followed by a long bearish candle
        # with a similar closing price.
        return self._is_bullish(i-1) and self._is_bearish(i) and \
               self._body(i-1) > self.body_size_threshold * 3 and \
               self._body(i) > self.body_size_threshold * 3 and \
               abs(self.data['Close'].iloc[i-1] - self.data['Close'].iloc[i]) < self.body_size_threshold

    def _is_bullish_separating_lines(self, i):
        if i < 1: return False
        # In an uptrend, a bearish candle is followed by a bullish candle
        # with the same opening price.
        return self._is_bearish(i-1) and self._is_bullish(i) and \
               abs(self.data['Open'].iloc[i-1] - self.data['Open'].iloc[i]) < self.body_size_threshold

    def _is_bearish_separating_lines(self, i):
        if i < 1: return False
        # In a downtrend, a bullish candle is followed by a bearish candle
        # with the same opening price.
        return self._is_bullish(i-1) and self._is_bearish(i) and \
               abs(self.data['Open'].iloc[i-1] - self.data['Open'].iloc[i]) < self.body_size_threshold

    def _is_bullish_kicking(self, i):
        if i < 1: return False
        # A bearish marubozu followed by a bullish marubozu with a gap up.
        return self._is_marubozu_black(i-1) and self._is_marubozu_white(i) and self._is_gap_up(i)

    def _is_bearish_kicking(self, i):
        if i < 1: return False
        # A bullish marubozu followed by a bearish marubozu with a gap down.
        return self._is_marubozu_white(i-1) and self._is_marubozu_black(i) and self._is_gap_down(i)

    def _is_homing_pigeon(self, i):
        if i < 1: return False
        # First day is a long black candle.
        if not (self._is_bearish(i-1) and self._body(i-1) > self.body_size_threshold * 3): return False
        # Second day is a smaller black candle completely inside the first day's body.
        return self._is_bearish(i) and \
               self.data['Open'].iloc[i] < self.data['Open'].iloc[i-1] and \
               self.data['Close'].iloc[i] > self.data['Close'].iloc[i-1]

    def _is_matching_low(self, i):
        if i < 1: return False
        # First day is a long black candle.
        if not (self._is_bearish(i-1) and self._body(i-1) > self.body_size_threshold * 3): return False
        # Second day is also a black candle with a close equal to the first day's close.
        return self._is_bearish(i) and \
               abs(self.data['Close'].iloc[i] - self.data['Close'].iloc[i-1]) < self.body_size_threshold

    def _is_counterattack_lines(self, i):
        if i < 1: return False
        # First candle has a large body.
        if not (self._body(i-1) > self.body_size_threshold * 3): return False
        # Second candle has an opposite color and a similar closing price.
        return (self._is_bullish(i) != self._is_bullish(i-1)) and \
               abs(self.data['Close'].iloc[i] - self.data['Close'].iloc[i-1]) < self.body_size_threshold

    def _is_hook_reversal(self, i):
        if i < 1: return False
        # Previous day has an opposite color.
        if self._is_bullish(i) == self._is_bullish(i-1): return False
        # Current day has a higher low and a lower high than the previous day.
        return self.data['Low'].iloc[i] > self.data['Low'].iloc[i-1] and \
               self.data['High'].iloc[i] < self.data['High'].iloc[i-1]

    # Three Candle Patterns
    def _is_morning_star(self, i):
        if i < 2: return False
        # First candle: long, bearish
        if not (self._is_bearish(i-2) and self._body(i-2) > self.body_size_threshold * 3): return False
        # Second candle: small body, gapped down
        if not (self._body(i-1) < self.body_size_threshold and self.data['Open'].iloc[i-1] < self.data['Close'].iloc[i-2]): return False
        # Third candle: bullish, closes within the first candle's body
        return self._is_bullish(i) and self.data['Close'].iloc[i] > self._real_body_center(i-2)

    def _is_evening_star(self, i):
        if i < 2: return False
        # First candle: long, bullish
        if not (self._is_bullish(i-2) and self._body(i-2) > self.body_size_threshold * 3): return False
        # Second candle: small body, gapped up
        if not (self._body(i-1) < self.body_size_threshold and self.data['Open'].iloc[i-1] > self.data['Close'].iloc[i-2]): return False
        # Third candle: bearish, closes within the first candle's body
        return self._is_bearish(i) and self.data['Close'].iloc[i] < self._real_body_center(i-2)

    def _is_three_white_soldiers(self, i):
        if i < 2: return False
        # Three consecutive long bullish candles
        if not (self._is_bullish(i) and self._is_bullish(i-1) and self._is_bullish(i-2)): return False
        if not (self._body(i) > self.body_size_threshold * 2 and self._body(i-1) > self.body_size_threshold * 2 and self._body(i-2) > self.body_size_threshold * 2): return False
        # Each opens within the previous body
        if not (self.data['Open'].iloc[i] > self.data['Open'].iloc[i-1] and self.data['Open'].iloc[i-1] > self.data['Open'].iloc[i-2]): return False
        # Each closes higher than the previous close
        return self.data['Close'].iloc[i] > self.data['Close'].iloc[i-1] and self.data['Close'].iloc[i-1] > self.data['Close'].iloc[i-2]

    def _is_three_black_crows(self, i):
        if i < 2: return False
        # Three consecutive long bearish candles
        if not (self._is_bearish(i) and self._is_bearish(i-1) and self._is_bearish(i-2)): return False
        if not (self._body(i) > self.body_size_threshold * 2 and self._body(i-1) > self.body_size_threshold * 2 and self._body(i-2) > self.body_size_threshold * 2): return False
        # Each opens within the previous body
        if not (self.data['Open'].iloc[i] < self.data['Open'].iloc[i-1] and self.data['Open'].iloc[i-1] < self.data['Open'].iloc[i-2]): return False
        # Each closes lower than the previous close
        return self.data['Close'].iloc[i] < self.data['Close'].iloc[i-1] and self.data['Close'].iloc[i-1] < self.data['Close'].iloc[i-2]

    def _is_three_inside_up(self, i):
        if i < 2: return False
        # A bullish harami pattern...
        if not self._is_bullish_harami(i-1): return False
        # ...followed by a bullish candle that closes above the first candle's high.
        return self._is_bullish(i) and self.data['Close'].iloc[i] > self.data['High'].iloc[i-2]

    def _is_three_inside_down(self, i):
        if i < 2: return False
        # A bearish harami pattern...
        if not self._is_bearish_harami(i-1): return False
        # ...followed by a bearish candle that closes below the first candle's low.
        return self._is_bearish(i) and self.data['Close'].iloc[i] < self.data['Low'].iloc[i-2]

    def _is_three_outside_up(self, i):
        if i < 2: return False
        # A bullish engulfing pattern...
        if not self._is_bullish_engulfing(i-1): return False
        # ...followed by a bullish candle that closes higher.
        return self._is_bullish(i) and self.data['Close'].iloc[i] > self.data['Close'].iloc[i-1]

    def _is_three_outside_down(self, i):
        if i < 2: return False
        # A bearish engulfing pattern...
        if not self._is_bearish_engulfing(i-1): return False
        # ...followed by a bearish candle that closes lower.
        return self._is_bearish(i) and self.data['Close'].iloc[i] < self.data['Close'].iloc[i-1]

    def _is_abandoned_baby_bullish(self, i):
        if i < 2: return False
        # First is a long bearish candle.
        if not (self._is_bearish(i-2) and self._body(i-2) > self.body_size_threshold * 3): return False
        # Second is a doji that gaps down.
        if not (self._is_doji(i-1) and self.data['High'].iloc[i-1] < self.data['Low'].iloc[i-2]): return False
        # Third is a bullish candle that gaps up and closes in the first candle's body.
        return self._is_bullish(i) and self.data['Low'].iloc[i] > self.data['High'].iloc[i-1] and \
               self.data['Close'].iloc[i] > self._real_body_center(i-2)

    def _is_abandoned_baby_bearish(self, i):
        if i < 2: return False
        # First is a long bullish candle.
        if not (self._is_bullish(i-2) and self._body(i-2) > self.body_size_threshold * 3): return False
        # Second is a doji that gaps up.
        if not (self._is_doji(i-1) and self.data['Low'].iloc[i-1] > self.data['High'].iloc[i-2]): return False
        # Third is a bearish candle that gaps down and closes in the first candle's body.
        return self._is_bearish(i) and self.data['High'].iloc[i] < self.data['Low'].iloc[i-1] and \
               self.data['Close'].iloc[i] < self._real_body_center(i-2)

    def _is_three_stars_in_the_south(self, i):
        if i < 2: return False
        # First is a long black candle with a long lower shadow.
        if not (self._is_bearish(i-2) and self._lower_shadow(i-2) > self._body(i-2)): return False
        # Second is smaller, black, with a low higher than the first.
        if not (self._is_bearish(i-1) and self._body(i-1) < self._body(i-2) and self.data['Low'].iloc[i-1] > self.data['Low'].iloc[i-2]): return False
        # Third is a small black marubozu inside the second's range.
        return self._is_marubozu_black(i) and self._body(i) < self.body_size_threshold and \
               self.data['High'].iloc[i] < self.data['High'].iloc[i-1] and self.data['Low'].iloc[i] > self.data['Low'].iloc[i-1]

    def _is_concealing_baby_swallow(self, i):
        if i < 3: return False
        # Two black marubozus in a downtrend.
        if not (self._is_marubozu_black(i-3) and self._is_marubozu_black(i-2)): return False
        # Third day is a black candle that gaps down but trades into the prior day's body.
        if not (self._is_bearish(i-1) and self.data['Open'].iloc[i-1] < self.data['Close'].iloc[i-2] and self.data['High'].iloc[i-1] > self.data['Open'].iloc[i-2]): return False
        # Fourth day is a black candle that completely engulfs the third day.
        return self._is_bearish(i) and self.data['High'].iloc[i] > self.data['High'].iloc[i-1] and self.data['Low'].iloc[i] < self.data['Low'].iloc[i-1]

    def _is_deliberation(self, i):
        if i < 2: return False
        # Follows three white soldiers pattern.
        if not self._is_three_white_soldiers(i): return False
        # The third soldier is a small spinning top, indicating indecision.
        return self._is_spinning_top(i)

    def _is_identical_three_crows(self, i):
        if i < 2: return False
        # Three long black candles.
        if not (self._is_bearish(i) and self._is_bearish(i-1) and self._is_bearish(i-2)): return False
        # Each opens at or very near the previous day's close.
        return abs(self.data['Open'].iloc[i] - self.data['Close'].iloc[i-1]) < self.body_size_threshold and \
               abs(self.data['Open'].iloc[i-1] - self.data['Close'].iloc[i-2]) < self.body_size_threshold

    def _is_unique_three_river_bottom(self, i):
        if i < 2: return False
        # First is a long black candle.
        if not (self._is_bearish(i-2) and self._body(i-2) > self.body_size_threshold * 3): return False
        # Second is a black harami.
        if not (self._is_bearish(i-1) and self.data['Open'].iloc[i-1] < self.data['Open'].iloc[i-2] and self.data['Close'].iloc[i-1] > self.data['Close'].iloc[i-2]): return False
        # Third is a white candle that closes below the second candle's close.
        return self._is_bullish(i) and self.data['Close'].iloc[i] < self.data['Close'].iloc[i-1]

    def _is_advance_block(self, i):
        if i < 2: return False
        # Three white candles.
        if not (self._is_bullish(i) and self._is_bullish(i-1) and self._is_bullish(i-2)): return False
        # Each candle opens within the previous body.
        if not (self.data['Open'].iloc[i] > self.data['Open'].iloc[i-1] and self.data['Open'].iloc[i-1] > self.data['Open'].iloc[i-2]): return False
        # Showing signs of weakening (smaller bodies or long upper shadows).
        return self._body(i) < self._body(i-1) or self._upper_shadow(i) > self._body(i)

    def _is_stalled_pattern(self, i):
        if i < 2: return False
        # Two long white candles in an uptrend.
        if not (self._is_bullish(i-2) and self._is_bullish(i-1) and self._body(i-2) > self.body_size_threshold * 2 and self._body(i-1) > self.body_size_threshold * 2): return False
        # Third candle is a small white candle that gaps up but fails to make a new high.
        return self._is_bullish(i) and self._body(i) < self.body_size_threshold * 2 and \
               self.data['Open'].iloc[i] > self.data['Close'].iloc[i-1] and self.data['High'].iloc[i] < self.data['High'].iloc[i-1]

    def _is_upside_gap_two_crows(self, i):
        if i < 2: return False
        # First day is a long white candle.
        if not (self._is_bullish(i-2) and self._body(i-2) > self.body_size_threshold * 3): return False
        # Second day is a black candle that gaps up.
        if not (self._is_bearish(i-1) and self.data['Open'].iloc[i-1] > self.data['Close'].iloc[i-2]): return False
        # Third day is a black candle that opens inside the second day's body and closes inside the first day's body.
        return self._is_bearish(i) and \
               self.data['Open'].iloc[i] > self.data['Close'].iloc[i-1] and self.data['Open'].iloc[i] < self.data['Open'].iloc[i-1] and \
               self.data['Close'].iloc[i] < self.data['Close'].iloc[i-2]

    def _is_rising_window(self, i):
        if i < 1: return False
        # A gap between the high of the previous candle and the low of the current candle.
        return self.data['Low'].iloc[i] > self.data['High'].iloc[i-1]

    def _is_falling_window(self, i):
        if i < 1: return False
        # A gap between the low of the previous candle and the high of the current candle.
        return self.data['High'].iloc[i] < self.data['Low'].iloc[i-1]

    def _is_stick_sandwich(self, i):
        if i < 2: return False
        # A black candle, a white candle above it, and a black candle with the same close as the first.
        return self._is_bearish(i-2) and self._is_bullish(i-1) and self._is_bearish(i) and \
               self.data['Close'].iloc[i-1] > self.data['Close'].iloc[i-2] and \
               abs(self.data['Close'].iloc[i] - self.data['Close'].iloc[i-2]) < self.body_size_threshold

    def _is_rising_three_methods(self, i):
        if i < 4: return False
        # Long white candle.
        if not (self._is_bullish(i-4) and self._body(i-4) > self.body_size_threshold * 3): return False
        # Three small bearish candles contained within the first candle's range.
        c1 = self._is_bearish(i-3) and self.data['High'].iloc[i-3] < self.data['High'].iloc[i-4] and self.data['Low'].iloc[i-3] > self.data['Low'].iloc[i-4]
        c2 = self._is_bearish(i-2) and self.data['High'].iloc[i-2] < self.data['High'].iloc[i-4] and self.data['Low'].iloc[i-2] > self.data['Low'].iloc[i-4]
        c3 = self._is_bearish(i-1) and self.data['High'].iloc[i-1] < self.data['High'].iloc[i-4] and self.data['Low'].iloc[i-1] > self.data['Low'].iloc[i-4]
        if not (c1 and c2 and c3): return False
        # A final long white candle that closes above the first candle's close.
        return self._is_bullish(i) and self._body(i) > self.body_size_threshold * 3 and self.data['Close'].iloc[i] > self.data['Close'].iloc[i-4]

    def _is_falling_three_methods(self, i):
        if i < 4: return False
        # Long black candle.
        if not (self._is_bearish(i-4) and self._body(i-4) > self.body_size_threshold * 3): return False
        # Three small bullish candles contained within the first candle's range.
        c1 = self._is_bullish(i-3) and self.data['High'].iloc[i-3] < self.data['High'].iloc[i-4] and self.data['Low'].iloc[i-3] > self.data['Low'].iloc[i-4]
        c2 = self._is_bullish(i-2) and self.data['High'].iloc[i-2] < self.data['High'].iloc[i-4] and self.data['Low'].iloc[i-2] > self.data['Low'].iloc[i-4]
        c3 = self._is_bullish(i-1) and self.data['High'].iloc[i-1] < self.data['High'].iloc[i-4] and self.data['Low'].iloc[i-1] > self.data['Low'].iloc[i-4]
        if not (c1 and c2 and c3): return False
        # A final long black candle that closes below the first candle's close.
        return self._is_bearish(i) and self._body(i) > self.body_size_threshold * 3 and self.data['Close'].iloc[i] < self.data['Close'].iloc[i-4]

    def _is_on_neck_line(self, i):
        if i < 1: return False
        # First day is a long black candle in a downtrend.
        if not (self._is_bearish(i-1) and self._body(i-1) > self.body_size_threshold * 3): return False
        # Second day is a white candle that opens below the low of the first, but closes near the low of the first.
        return self._is_bullish(i) and self.data['Open'].iloc[i] < self.data['Low'].iloc[i-1] and \
               abs(self.data['Close'].iloc[i] - self.data['Low'].iloc[i-1]) < self.body_size_threshold

    def _is_in_neck_line(self, i):
        if i < 1: return False
        # First day is a long black candle in a downtrend.
        if not (self._is_bearish(i-1) and self._body(i-1) > self.body_size_threshold * 3): return False
        # Second day is a white candle that opens below the low, but closes slightly into the body of the first.
        return self._is_bullish(i) and self.data['Open'].iloc[i] < self.data['Low'].iloc[i-1] and \
               self.data['Close'].iloc[i] > self.data['Close'].iloc[i-1] and \
               abs(self.data['Close'].iloc[i] - self.data['Close'].iloc[i-1]) < self.body_size_threshold * 2

    def _is_thrusting_line(self, i):
        if i < 1: return False
        # First day is a long black candle in a downtrend.
        if not (self._is_bearish(i-1) and self._body(i-1) > self.body_size_threshold * 3): return False
        # Second day is a white candle that opens below the low, but closes below the midpoint of the first day's body.
        return self._is_bullish(i) and self.data['Open'].iloc[i] < self.data['Low'].iloc[i-1] and \
               self.data['Close'].iloc[i] < self._real_body_center(i-1) and \
               self.data['Close'].iloc[i] > self.data['Close'].iloc[i-1]

    def _is_downside_gap_three_methods(self, i):
        if i < 4: return False
        # First candle: long black candle
        c1 = self._is_bearish(i-4) and self._body(i-4) > self.body_size_threshold * 3
        if not c1: return False

        # Second candle: small bullish candle, opens with a gap down from the first
        c2 = self._is_bullish(i-3) and self._body(i-3) < self.body_size_threshold * 2 and \
             self.data['Open'].iloc[i-3] < self.data['Close'].iloc[i-4]
        if not c2: return False

        # Third and fourth candles: small bullish candles, contained within the range of the first candle
        c3 = self._is_bullish(i-2) and self._body(i-2) < self.body_size_threshold * 2 and \
             self.data['Low'].iloc[i-2] > self.data['Low'].iloc[i-4] and self.data['High'].iloc[i-2] < self.data['High'].iloc[i-4]
        c4 = self._is_bullish(i-1) and self._body(i-1) < self.body_size_threshold * 2 and \
             self.data['Low'].iloc[i-1] > self.data['Low'].iloc[i-4] and self.data['High'].iloc[i-1] < self.data['High'].iloc[i-4]
        if not (c3 and c4): return False

        # Fifth candle: long black candle, closes below the first candle's close
        c5 = self._is_bearish(i) and self._body(i) > self.body_size_threshold * 3 and \
             self.data['Close'].iloc[i] < self.data['Close'].iloc[i-4]
        return c5

    def _is_ladder_bottom(self, i):
        if i < 4: return False
        # Candle 1 (i-4): Long black candle
        c1 = self._is_bearish(i-4) and self._body(i-4) > self.body_size_threshold * 3
        if not c1: return False

        # Candle 2 (i-3): Black candle, closes lower than Candle 1
        c2 = self._is_bearish(i-3) and self.data['Close'].iloc[i-3] < self.data['Close'].iloc[i-4]
        if not c2: return False

        # Candle 3 (i-2): Black candle, closes lower than Candle 2
        c3 = self._is_bearish(i-2) and self.data['Close'].iloc[i-2] < self.data['Close'].iloc[i-3]
        if not c3: return False

        # Candle 4 (i-1): Black candle, with a small body and a long upper shadow. Opens within body of Candle 3.
        c4 = self._is_bearish(i-1) and self._body(i-1) < self.body_size_threshold * 2 and \
             self._upper_shadow(i-1) > self._body(i-1) * 2 and \
             self.data['Open'].iloc[i-1] > self.data['Close'].iloc[i-2] and self.data['Open'].iloc[i-1] < self.data['Open'].iloc[i-2]
        if not c4: return False

        # Candle 5 (i): Long white candle that opens above the high of Candle 4 and closes above the high of Candle 3.
        c5 = self._is_bullish(i) and self._body(i) > self.body_size_threshold * 3 and \
             self.data['Open'].iloc[i] > self.data['High'].iloc[i-1] and \
             self.data['Close'].iloc[i] > self.data['High'].iloc[i-2]
        return c5

    def _is_breakaway(self, i):
        if i < 4: return False
        # Candle 1 (i-4): Long black candle.
        c1 = self._is_bearish(i-4) and self._body(i-4) > self.body_size_threshold * 3
        if not c1: return False

        # Candles 2 (i-3), 3 (i-2), 4 (i-1): Small-bodied, gapping down, contained within Candle 1's range.
        c2 = self._body(i-3) < self.body_size_threshold * 2 and self._is_gap_down(i-3) and \
             self.data['Low'].iloc[i-3] > self.data['Low'].iloc[i-4] and self.data['High'].iloc[i-3] < self.data['High'].iloc[i-4]
        c3 = self._body(i-2) < self.body_size_threshold * 2 and self._is_gap_down(i-2) and \
             self.data['Low'].iloc[i-2] > self.data['Low'].iloc[i-4] and self.data['High'].iloc[i-2] < self.data['High'].iloc[i-4]
        c4 = self._body(i-1) < self.body_size_threshold * 2 and self._is_gap_down(i-1) and \
             self.data['Low'].iloc[i-1] > self.data['Low'].iloc[i-4] and self.data['High'].iloc[i-1] < self.data['High'].iloc[i-4]
        if not (c2 and c3 and c4): return False

        # Candle 5 (i): Long white candle that opens above the close of Candle 4 and closes above the high of Candle 1.
        c5 = self._is_bullish(i) and self._body(i) > self.body_size_threshold * 3 and \
             self.data['Open'].iloc[i] > self.data['Close'].iloc[i-1] and \
             self.data['Close'].iloc[i] > self.data['High'].iloc[i-4]
        return c5

    def _is_side_by_side_white_lines_bullish(self, i):
        if i < 2: return False
        # Candle 1 (i-2): Long white candle.
        c1 = self._is_bullish(i-2) and self._body(i-2) > self.body_size_threshold * 3
        if not c1: return False

        # Candle 2 (i-1): White candle, opens with a gap up from Candle 1, similar open/close to Candle 1.
        c2 = self._is_bullish(i-1) and self._is_gap_up(i-1) and \
             abs(self.data['Open'].iloc[i-1] - self.data['Open'].iloc[i-2]) < self.body_size_threshold * 2 and \
             abs(self.data['Close'].iloc[i-1] - self.data['Close'].iloc[i-2]) < self.body_size_threshold * 2
        if not c2: return False

        # Candle 3 (i): White candle, opens with a gap up from Candle 2, similar open/close to Candle 2.
        c3 = self._is_bullish(i) and self._is_gap_up(i) and \
             abs(self.data['Open'].iloc[i] - self.data['Open'].iloc[i-1]) < self.body_size_threshold * 2 and \
             abs(self.data['Close'].iloc[i] - self.data['Close'].iloc[i-1]) < self.body_size_threshold * 2
        return c3

    def _is_side_by_side_white_lines_bearish(self, i):
        if i < 2: return False
        # Candle 1 (i-2): Long black candle.
        c1 = self._is_bearish(i-2) and self._body(i-2) > self.body_size_threshold * 3
        if not c1: return False

        # Candle 2 (i-1): Black candle, opens with a gap down from Candle 1, similar open/close to Candle 1.
        c2 = self._is_bearish(i-1) and self._is_gap_down(i-1) and \
             abs(self.data['Open'].iloc[i-1] - self.data['Open'].iloc[i-2]) < self.body_size_threshold * 2 and \
             abs(self.data['Close'].iloc[i-1] - self.data['Close'].iloc[i-2]) < self.body_size_threshold * 2
        if not c2: return False

        # Candle 3 (i): Black candle, opens with a gap down from Candle 2, similar open/close to Candle 2.
        c3 = self._is_bearish(i) and self._is_gap_down(i) and \
             abs(self.data['Open'].iloc[i] - self.data['Open'].iloc[i-1]) < self.body_size_threshold * 2 and \
             abs(self.data['Close'].iloc[i] - self.data['Close'].iloc[i-1]) < self.body_size_threshold * 2
        return c3

    def _is_tasuki_gap_up(self, i):
        if i < 2: return False
        # Candle 1 (i-2): White candle.
        c1 = self._is_bullish(i-2)
        if not c1: return False

        # Candle 2 (i-1): White candle that gaps up from Candle 1.
        c2 = self._is_bullish(i-1) and self._is_gap_up(i-1)
        if not c2: return False

        # Candle 3 (i): Black candle that opens within the body of Candle 2 and closes within the gap.
        c3 = self._is_bearish(i) and \
             self.data['Open'].iloc[i] > self.data['Open'].iloc[i-1] and self.data['Open'].iloc[i] < self.data['Close'].iloc[i-1] and \
             self.data['Close'].iloc[i] > self.data['Close'].iloc[i-2] and self.data['Close'].iloc[i] < self.data['Open'].iloc[i-1]
        return c3
