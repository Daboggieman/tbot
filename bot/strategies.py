import pandas as pd
import numpy as np

class MovingAverageCrossoverStrategy:
    """
    A simple moving average crossover strategy.
    """
    def __init__(self, short_window=40, long_window=100):
        """
        Initializes the MovingAverageCrossoverStrategy.

        Args:
            short_window (int): The short window for the moving average.
            long_window (int): The long window for the moving average.
        """
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data):
        """
        Generates trading signals for the given data.

        Args:
            data (pd.DataFrame): The historical market data.

        Returns:
            pd.DataFrame: The data with a 'signal' column.
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Create short simple moving average
        signals['short_mavg'] = data['Close'].rolling(window=self.short_window, min_periods=1, center=False).mean()

        # Create long simple moving average
        signals['long_mavg'] = data['Close'].rolling(window=self.long_window, min_periods=1, center=False).mean()

        # Create signals
        signals.loc[signals.index[self.short_window:], 'signal'] = np.where(signals['short_mavg'][self.short_window:] 
                                                                            > signals['long_mavg'][self.short_window:], 1.0, 0.0)

        # Generate trading events
        signals['positions'] = signals['signal'].diff()

        return signals


class SentimentAwareMovingAverageCrossoverStrategy:
    """
    A moving average crossover strategy that incorporates sentiment analysis.
    """
    def __init__(self, short_window=40, long_window=100, sentiment_threshold=0.1):
        """
        Initializes the SentimentAwareMovingAverageCrossoverStrategy.

        Args:
            short_window (int): The short window for the moving average.
            long_window (int): The long window for the moving average.
            sentiment_threshold (float): The sentiment threshold for generating signals.
        """
        self.short_window = short_window
        self.long_window = long_window
        self.sentiment_threshold = sentiment_threshold

    def generate_signals(self, data, sentiment_series):
        """
        Generates trading signals for the given data, incorporating sentiment.

        Args:
            data (pd.DataFrame): The historical market data.
            sentiment_series (pd.Series): The sentiment scores for each timestamp.

        Returns:
            pd.DataFrame: The data with a 'signal' column.
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Create short simple moving average
        signals['short_mavg'] = data['Close'].rolling(window=self.short_window, min_periods=1, center=False).mean()

        # Create long simple moving average
        signals['long_mavg'] = data['Close'].rolling(window=self.long_window, min_periods=1, center=False).mean()

        # Create signals based on moving average crossover
        signals['crossover_signal'] = np.where(signals['short_mavg'] > signals['long_mavg'], 1.0, -1.0)

        # Incorporate sentiment
        signals['sentiment'] = sentiment_series
        signals.loc[(signals['crossover_signal'] == 1.0) & (signals['sentiment'] > self.sentiment_threshold), 'signal'] = 1.0
        signals.loc[(signals['crossover_signal'] == -1.0) & (signals['sentiment'] < -self.sentiment_threshold), 'signal'] = -1.0

        # Generate trading events
        signals['positions'] = signals['signal'].diff()

        return signals



class CandlestickPatternStrategy:
    """
    A strategy that trades based on identified candlestick patterns.
    """
    def __init__(self):
        pass

    def generate_signals(self, data):
        """
        Generates trading signals for the given data.

        Args:
            data (pd.DataFrame): The historical market data with pattern columns.

        Returns:
            pd.DataFrame: The data with a 'signal' column.
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Buy signal on Bullish Engulfing, Hammer, Morning Star, or Piercing Line
        signals.loc[data['bullish_engulfing'] | data['hammer'] | data['morning_star'] | data['piercing_line'], 'signal'] = 1.0

        # Sell signal on Bearish Engulfing, Evening Star, or Dark Cloud Cover
        signals.loc[data['bearish_engulfing'] | data['evening_star'] | data['dark_cloud_cover'], 'signal'] = -1.0

        # Generate trading events
        signals['positions'] = signals['signal'].diff()

        return signals


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

        return signals


class MACDStrategy:
    """
    A strategy based on the Moving Average Convergence Divergence (MACD).
    """
    def __init__(self, fast_window=12, slow_window=26, signal_window=9):
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.signal_window = signal_window

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        exp1 = data['Close'].ewm(span=self.fast_window, adjust=False).mean()
        exp2 = data['Close'].ewm(span=self.slow_window, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=self.signal_window, adjust=False).mean()

        signals.loc[macd > signal, 'signal'] = 1.0
        signals.loc[macd < signal, 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals


class BollingerBandsMeanReversionStrategy:
    """
    A strategy based on Bollinger Bands.
    """
    def __init__(self, window=20, num_std_dev=2):
        self.window = window
        self.num_std_dev = num_std_dev

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Bollinger Bands
        rolling_mean = data['Close'].rolling(window=self.window).mean()
        rolling_std = data['Close'].rolling(window=self.window).std()

        upper_band = rolling_mean + (rolling_std * self.num_std_dev)
        lower_band = rolling_mean - (rolling_std * self.num_std_dev)

        # Generate signals
        signals.loc[data['Close'] < lower_band, 'signal'] = 1.0  # Buy when price crosses below lower band
        signals.loc[data['Close'] > upper_band, 'signal'] = -1.0 # Sell when price crosses above upper band

        signals['positions'] = signals['signal'].diff()

        return signals

class BollingerBandsSqueezeStrategy:
    """
    A strategy that identifies a Bollinger Bands squeeze and trades the breakout.
    """
    def __init__(self, window=20, num_std_dev=2, squeeze_threshold=2.33):
        self.window = window
        self.num_std_dev = num_std_dev
        self.squeeze_threshold = squeeze_threshold

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Bollinger Bands
        rolling_mean = data['Close'].rolling(window=self.window).mean()
        rolling_std = data['Close'].rolling(window=self.window).std()

        upper_band = rolling_mean + (rolling_std * self.num_std_dev)
        lower_band = rolling_mean - (rolling_std * self.num_std_dev)

        # Calculate Bollinger Bandwidth
        bandwidth = ((upper_band - lower_band) / rolling_mean) * 100
        
        # Identify squeeze
        squeeze = bandwidth < self.squeeze_threshold

        # Generate signals on breakout
        signals.loc[(squeeze.shift(1)) & (data['Close'] > upper_band), 'signal'] = 1.0  # Buy on breakout
        signals.loc[(squeeze.shift(1)) & (data['Close'] < lower_band), 'signal'] = -1.0 # Sell on breakout

        signals['positions'] = signals['signal'].diff()

        return signals



class DMIADXStrategy:
    """
    A strategy based on the Directional Movement Index (DMI) and Average Directional Index (ADX).
    """
    def __init__(self, window=14, adx_threshold=25):
        self.window = window
        self.adx_threshold = adx_threshold

    def generate_signals(self, data):
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

        return signals


class ParabolicSARStrategy:
    """
    A strategy based on the Parabolic SAR indicator.
    """
    def __init__(self, af_start=0.02, af_increment=0.02, af_max=0.2):
        self.af_start = af_start
        self.af_increment = af_increment
        self.af_max = af_max

    def generate_signals(self, data):
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

        return signals


class IchimokuStrategy:
    """
    A strategy based on the Ichimoku Kinko Hyo indicator.
    """
    def __init__(self, tenkan_window=9, kijun_window=26, senkou_window=52):
        self.tenkan_window = tenkan_window
        self.kijun_window = kijun_window
        self.senkou_window = senkou_window

    def generate_signals(self, data):
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
        import logging
        logger = logging.getLogger(__name__)
        logger.info("--- Ichimoku Debug ---")
        logger.info(f"Tenkan-sen:\n{tenkan_sen.tail()}")
        logger.info(f"Kijun-sen:\n{kijun_sen.tail()}")
        logger.info(f"Signals:\n{signals.tail()}")
        logger.info("--- End Ichimoku Debug ---")

        return signals


class StochasticOscillatorStrategy:
    """
    A strategy based on the Stochastic Oscillator.
    """
    def __init__(self, k_window=14, d_window=3, buy_threshold=20, sell_threshold=80):
        self.k_window = k_window
        self.d_window = d_window
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate %K
        lowest_low = data['Low'].rolling(window=self.k_window).min()
        highest_high = data['High'].rolling(window=self.k_window).max()
        percent_k = ((data['Close'] - lowest_low) / (highest_high - lowest_low)) * 100

        # Calculate %D (3-period SMA of %K)
        percent_d = percent_k.rolling(window=self.d_window).mean()

        # Generate signals
        # Buy signal: %K crosses above %D and both are below buy_threshold
        signals.loc[(percent_k > percent_d) & (percent_k.shift(1) <= percent_d.shift(1)) & (percent_k < self.buy_threshold), 'signal'] = 1.0
        # Sell signal: %K crosses below %D and both are above sell_threshold
        signals.loc[(percent_k < percent_d) & (percent_k.shift(1) >= percent_d.shift(1)) & (percent_k > self.sell_threshold), 'signal'] = -1.0

        signals['positions'] = signals['signal'].diff()

        return signals


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

        return signals

class ROCStrategy:
    """
    A strategy based on the Price Rate of Change (ROC) indicator.
    """
    def __init__(self, window=12, buy_threshold=0, sell_threshold=0):
        self.window = window
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate ROC
        roc = ((data['Close'] - data['Close'].shift(self.window)) / data['Close'].shift(self.window)) * 100

        # Generate signals
        signals.loc[roc > self.buy_threshold, 'signal'] = 1.0  # Buy when ROC is above buy_threshold
        signals.loc[roc < self.sell_threshold, 'signal'] = -1.0 # Sell when ROC is below sell_threshold

        signals['positions'] = signals['signal'].diff()

        return signals

class MomentumStrategy:
    """
    A strategy based on the Momentum indicator.
    """
    def __init__(self, window=14):
        self.window = window

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate Momentum
        momentum = data['Close'] - data['Close'].shift(self.window)

        # Generate signals
        signals.loc[momentum > 0, 'signal'] = 1.0  # Buy when momentum is positive
        signals.loc[momentum < 0, 'signal'] = -1.0 # Sell when momentum is negative

        signals['positions'] = signals['signal'].diff()

        return signals

class ATRBreakoutStrategy:
    """
    A strategy based on the Average True Range (ATR) breakout.
    """
    def __init__(self, atr_window=14, ma_window=20, atr_multiplier=2.0):
        self.atr_window = atr_window
        self.ma_window = ma_window
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, data):
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

        return signals

class KeltnerChannelsStrategy:
    """
    A strategy based on Keltner Channels.
    """
    def __init__(self, ema_window=20, atr_window=10, atr_multiplier=2.0):
        self.ema_window = ema_window
        self.atr_window = atr_window
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate EMA
        ema = data['Close'].ewm(span=self.ema_window, adjust=False).mean()

        # Calculate True Range (TR)
        tr1 = data['High'] - data['Low']
        tr2 = abs(data['High'] - data['Close'].shift(1))
        tr3 = abs(data['Low'] - data['Close'].shift(1))
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)

        # Calculate ATR
        atr = tr.ewm(span=self.atr_window, adjust=False).mean()

        # Calculate Keltner Channels
        upper_channel = ema + (self.atr_multiplier * atr)
        lower_channel = ema - (self.atr_multiplier * atr)

        # Generate signals
        signals.loc[data['Close'] > upper_channel, 'signal'] = 1.0  # Buy on breakout above upper channel
        signals.loc[data['Close'] < lower_channel, 'signal'] = -1.0 # Sell on breakout below lower channel

        signals['positions'] = signals['signal'].diff()

        return signals

class OBVStrategy:
    """
    A strategy based on the On-Balance Volume (OBV) indicator.
    """
    def __init__(self):
        pass

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate OBV
        obv = (np.sign(data['Close'].diff()) * data['Volume']).fillna(0).cumsum()

        # Generate signals
        signals.loc[obv > obv.shift(1), 'signal'] = 1.0  # Buy when OBV is rising
        signals.loc[obv < obv.shift(1), 'signal'] = -1.0 # Sell when OBV is falling

        signals['positions'] = signals['signal'].diff()

        return signals

class VPTStrategy:
    """
    A strategy based on the Volume Price Trend (VPT) indicator.
    """
    def __init__(self, vpt_window=20):
        self.vpt_window = vpt_window

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate VPT
        vpt = (data['Volume'] * ((data['Close'] - data['Close'].shift(1)) / data['Close'].shift(1))).fillna(0).cumsum()

        # Calculate VPT moving average
        vpt_ma = vpt.rolling(window=self.vpt_window).mean()

        # Generate signals
        signals.loc[vpt > vpt_ma, 'signal'] = 1.0  # Buy when VPT is above its moving average
        signals.loc[vpt < vpt_ma, 'signal'] = -1.0 # Sell when VPT is below its moving average

        signals['positions'] = signals['signal'].diff()

        return signals

class ArbitrageStrategy:
    """
    A conceptual strategy for identifying arbitrage opportunities between two data sources.
    """
    def __init__(self, threshold=0.001):
        self.threshold = threshold

    def generate_signals(self, data_a, data_b):
        """
        Generates trading signals based on price differences between two data sources.

        Args:
            data_a (pd.DataFrame): The historical market data from source A.
            data_b (pd.DataFrame): The historical market data from source B.

        Returns:
            pd.DataFrame: A DataFrame with signals for both sources.
        """
        signals = pd.DataFrame(index=data_a.index)
        signals['signal_a'] = 0.0
        signals['signal_b'] = 0.0

        # Calculate price difference
        price_diff = data_a['Close'] - data_b['Close']

        # Generate signals
        signals.loc[price_diff > self.threshold, 'signal_a'] = -1.0 # Sell on source A
        signals.loc[price_diff > self.threshold, 'signal_b'] = 1.0  # Buy on source B

        signals.loc[price_diff < -self.threshold, 'signal_a'] = 1.0  # Buy on source A
        signals.loc[price_diff < -self.threshold, 'signal_b'] = -1.0 # Sell on source B

        signals['positions_a'] = signals['signal_a'].diff()
        signals['positions_b'] = signals['signal_b'].diff()

        return signals


class PairsTradingStrategy:
    """
    A strategy that trades on the divergence and convergence of two correlated assets.
    """
    def __init__(self, window=20, threshold=1.5):
        self.window = window
        self.threshold = threshold

    def generate_signals(self, data_a, data_b):
        """
        Generates trading signals based on the spread between two assets.

        Args:
            data_a (pd.DataFrame): The historical market data for asset A.
            data_b (pd.DataFrame): The historical market data for asset B.

        Returns:
            pd.DataFrame: A DataFrame with signals for both assets.
        """
        signals = pd.DataFrame(index=data_a.index)
        signals['signal_a'] = 0.0
        signals['signal_b'] = 0.0

        # Calculate the spread
        spread = data_a['Close'] - data_b['Close']

        # Calculate the moving average and standard deviation of the spread
        spread_mavg = spread.rolling(window=self.window).mean()
        spread_std = spread.rolling(window=self.window).std()

        # Calculate the z-score of the spread
        z_score = (spread - spread_mavg) / spread_std

        # Generate signals
        # Short the spread (short A, long B) when z-score is high
        signals.loc[z_score > self.threshold, 'signal_a'] = -1.0
        signals.loc[z_score > self.threshold, 'signal_b'] = 1.0

        # Long the spread (long A, short B) when z-score is low
        signals.loc[z_score < -self.threshold, 'signal_a'] = 1.0
        signals.loc[z_score < -self.threshold, 'signal_b'] = -1.0

        # Exit when the z-score crosses zero
        signals.loc[z_score.abs() < 0.5, 'signal_a'] = 0.0
        signals.loc[z_score.abs() < 0.5, 'signal_b'] = 0.0

        signals['positions_a'] = signals['signal_a'].diff()
        signals['positions_b'] = signals['signal_b'].diff()

        return signals

class EventDrivenStrategy:
    """
    A strategy that generates signals based on real-time market events.
    """
    def __init__(self, news_sentiment_threshold=0.5, holding_period=5):
        self.news_sentiment_threshold = news_sentiment_threshold
        self.holding_period = holding_period
        self.position = 0  # -1 for short, 0 for flat, 1 for long
        self.entry_bar = -1

    def generate_signal(self, event, current_bar=None):
        """
        Generates a trading signal for a single market event.

        Args:
            event (dict): A dictionary representing a single market event.
            current_bar (int): The index of the current bar.

        Returns:
            dict: A dictionary representing a trading signal.
        """
        signal = {'signal': 'HOLD', 'symbol': event.get('symbol')}

        # If we are in a position, check if we should exit
        if self.position != 0 and current_bar is not None:
            if current_bar - self.entry_bar >= self.holding_period:
                signal['signal'] = 'SELL' if self.position == 1 else 'BUY'
                self.position = 0
                self.entry_bar = -1
                return signal

        # If we are flat, check for an entry signal
        if self.position == 0 and event.get('type') == 'news' and 'sentiment' in event:
            if event['sentiment'] > self.news_sentiment_threshold:
                signal['signal'] = 'BUY'
                self.position = 1
                self.entry_bar = current_bar
            elif event['sentiment'] < -self.news_sentiment_threshold:
                signal['signal'] = 'SELL'
                self.position = -1
                self.entry_bar = current_bar

        return signal

class IntermarketAwareMovingAverageCrossoverStrategy:
    """
    A moving average crossover strategy that incorporates intermarket analysis.
    """
    def __init__(self, short_window=40, long_window=100, correlation_window=20, correlation_threshold=0.5):
        """
        Initializes the IntermarketAwareMovingAverageCrossoverStrategy.

        Args:
            short_window (int): The short window for the moving average.
            long_window (int): The long window for the moving average.
            correlation_window (int): The window for calculating the correlation.
            correlation_threshold (float): The correlation threshold for generating signals.
        """
        self.short_window = short_window
        self.long_window = long_window
        self.correlation_window = correlation_window
        self.correlation_threshold = correlation_threshold

    def generate_signals(self, primary_data, secondary_data):
        """
        Generates trading signals for the given data, incorporating intermarket analysis.

        Args:
            primary_data (pd.DataFrame): The historical market data for the primary asset.
            secondary_data (pd.DataFrame): The historical market data for the secondary asset.

        Returns:
            pd.DataFrame: The data with a 'signal' column.
        """
        signals = pd.DataFrame(index=primary_data.index)
        signals['signal'] = 0.0

        # Create short simple moving average for the primary asset
        signals['short_mavg'] = primary_data['Close'].rolling(window=self.short_window, min_periods=1, center=False).mean()

        # Create long simple moving average for the primary asset
        signals['long_mavg'] = primary_data['Close'].rolling(window=self.long_window, min_periods=1, center=False).mean()

        # Create signals based on moving average crossover
        signals['crossover_signal'] = np.where(signals['short_mavg'] > signals['long_mavg'], 1.0, -1.0)

        # Calculate the correlation between the primary and secondary assets
        correlation = primary_data['Close'].rolling(window=self.correlation_window).corr(secondary_data['Close'])
        signals['correlation'] = correlation

        # Incorporate intermarket analysis
        signals.loc[(signals['crossover_signal'] == 1.0) & (signals['correlation'] > self.correlation_threshold), 'signal'] = 1.0
        signals.loc[(signals['crossover_signal'] == -1.0) & (signals['correlation'] < -self.correlation_threshold), 'signal'] = -1.0

        # Generate trading events
        signals['positions'] = signals['signal'].diff()

        return signals
