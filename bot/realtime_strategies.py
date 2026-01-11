import pandas as pd
from datetime import datetime, timezone
from market_context_analyzer import MarketContextAnalyzer
from abc import ABC, abstractmethod
from collections import deque
import numpy as np

class BaseRealtimeStrategy(ABC):
    """
    Abstract base class for all real-time trading strategies.
    It defines a common interface for signal generation.
    """
    def __init__(self, symbol: str, data: pd.DataFrame, **kwargs):
        self.symbol = symbol
        self.data = data
        self.positions = [] # List of open positions

    @abstractmethod
    def generate_signal(self, context: dict) -> str:
        """
        Generate a trading signal based on the provided market context.

        Args:
            context (dict): A dictionary containing all relevant data for decision-making,
                            such as 'tick_data', 'market_data', 'sentiment_score', 'themes',
                            'detected_patterns', 'market_analyzer'.

        Returns:
            str: 'BUY', 'SELL', or 'HOLD'.
        """
        pass

class RealtimeMovingAverageCrossoverStrategy(BaseRealtimeStrategy):
    """A real-time moving average crossover strategy."""
    def __init__(self, symbol: str, data: pd.DataFrame, short_window: int, long_window: int, **kwargs):
        super().__init__(symbol, data)
        self.short_window = short_window
        self.long_window = long_window

    def generate_signal(self, context: dict) -> str:
        """Generates a signal based on moving average crossover."""
        market_data = context.get('market_data')
        if market_data is None or len(market_data) < self.long_window:
            print(f"[DEBUG] Holding: Not enough data ({len(market_data) if market_data is not None else 0}/{self.long_window})")
            return 'HOLD'

        # Use a copy to avoid SettingWithCopyWarning
        data = market_data.copy()
        data['short_ma'] = data['close'].rolling(window=self.short_window).mean()
        data['long_ma'] = data['close'].rolling(window=self.long_window).mean()

        if data.empty or len(data) < 2:
            return 'HOLD'

        latest = data.iloc[-1]
        previous = data.iloc[-2]

        print(f"[DEBUG] MA Crossover Check: Short MA={latest['short_ma']:.5f}, Long MA={latest['long_ma']:.5f}")

        # Crossover conditions
        if latest['short_ma'] > latest['long_ma'] and previous['short_ma'] <= previous['long_ma']:
            print("[DEBUG] MA Crossover: BUY SIGNAL")
            return 'BUY'
        elif latest['short_ma'] < latest['long_ma'] and previous['short_ma'] >= previous['long_ma']:
            print("[DEBUG] MA Crossover: SELL SIGNAL")
            return 'SELL'
        else:
            return 'HOLD'

class RealtimeSentimentAwareMovingAverageCrossoverStrategy(RealtimeMovingAverageCrossoverStrategy):
    """Extends the MA crossover strategy with a sentiment filter."""
    def __init__(self, symbol: str, data: pd.DataFrame, short_window: int, long_window: int, sentiment_threshold: float, **kwargs):
        super().__init__(symbol, data, short_window=short_window, long_window=long_window)
        self.sentiment_threshold = sentiment_threshold

    def generate_signal(self, context: dict) -> str:
        """Generates a signal only if sentiment is favorable."""
        sentiment_score = context.get('sentiment_score', 0.0)
        base_signal = super().generate_signal(context)

        if base_signal == 'BUY' and sentiment_score > self.sentiment_threshold:
            return 'BUY'
        elif base_signal == 'SELL' and sentiment_score < -self.sentiment_threshold:
            return 'SELL'
        else:
            return 'HOLD'

class RealtimeIntermarketAwareMovingAverageCrossoverStrategy(RealtimeMovingAverageCrossoverStrategy):
    """Extends the MA crossover strategy with an intermarket correlation filter."""
    def __init__(self, symbol: str, data: pd.DataFrame, short_window: int, long_window: int, market_context_analyzer: MarketContextAnalyzer, correlation_symbol: str, **kwargs):
        super().__init__(symbol, data, short_window=short_window, long_window=long_window)
        self.market_context_analyzer = market_context_analyzer
        self.correlation_symbol = correlation_symbol

    def generate_signal(self, context: dict) -> str:
        """Generates a signal only if intermarket correlation is favorable."""
        base_signal = super().generate_signal(context)
        
        if not self.market_context_analyzer:
            return base_signal

        correlation = self.market_context_analyzer.get_correlation(self.symbol, self.correlation_symbol)
        
        if correlation is None:
            return 'HOLD'

        if base_signal != 'HOLD' and correlation > 0.1:
            return base_signal
        else:
            return 'HOLD'

class RealtimeThematicStrategy(BaseRealtimeStrategy):
    """A strategy that trades based on detected news themes."""
    def __init__(self, symbol: str, data: pd.DataFrame, required_themes: list, **kwargs):
        super().__init__(symbol, data)
        self.required_themes = required_themes

    def generate_signal(self, context: dict) -> str:
        """Generates a signal if required themes are present in the news."""
        themes = context.get('themes', [])
        sentiment_score = context.get('sentiment_score', 0.0)

        has_required_theme = any(theme in themes for theme in self.required_themes)

        if has_required_theme:
            if sentiment_score > 0.2:
                return 'BUY'
            elif sentiment_score < -0.2:
                return 'SELL'
        
        return 'HOLD'

class RealtimePatternBasedStrategy(BaseRealtimeStrategy):
    """A strategy that trades based on detected candlestick patterns."""
    def __init__(self, symbol: str, data: pd.DataFrame, patterns_to_use: list, **kwargs):
        super().__init__(symbol, data)
        self.patterns_to_use = patterns_to_use

    def generate_signal(self, context: dict) -> str:
        """Generates a signal based on the latest detected patterns."""
        detected_patterns = context.get('detected_patterns', [])
        if not detected_patterns:
            return 'HOLD'

        for pattern in detected_patterns:
            pattern_name = pattern.get('name')
            if self.patterns_to_use == ['all'] or pattern_name in self.patterns_to_use:
                if pattern.get('type') == 'bullish':
                    return 'BUY'
                elif pattern.get('type') == 'bearish':
                    return 'SELL'
        
        return 'HOLD'

class RealtimeStandardStrategy(BaseRealtimeStrategy):
    """
    A generic real-time wrapper for any modular strategy from bot.strategies.
    It applies the strategy to a window of real-time data to extract the latest signal.
    """
    def __init__(self, symbol: str, data: pd.DataFrame, strategy_class, **kwargs):
        super().__init__(symbol, data)
        # Create an instance of the modular strategy with the provided kwargs (params)
        self.modular_strategy = strategy_class(**kwargs)

    def generate_signal(self, context: dict) -> str:
        """
        Generates a signal by running the modular strategy on the latest market data.
        """
        market_data = context.get('market_data')
        
        # We need enough data for the strategy to calculate its indicators.
        if market_data is None or market_data.empty:
            return 'HOLD'

        try:
            # Generate signals for the entire available window
            signals_df = self.modular_strategy.generate_signals(market_data)
            
            if signals_df.empty:
                return 'HOLD'

            # Extract the latest signal
            latest_signal = signals_df['signal'].iloc[-1]
            
            if latest_signal == 1.0:
                print(f"[DEBUG] {self.modular_strategy.__class__.__name__}: BUY SIGNAL")
                return 'BUY'
            elif latest_signal == -1.0:
                print(f"[DEBUG] {self.modular_strategy.__class__.__name__}: SELL SIGNAL")
                return 'SELL'
            else:
                return 'HOLD'
        except Exception as e:
            print(f"[ERROR] RealtimeStandardStrategy failed to generate signal: {e}")
            return 'HOLD'
