from collections import deque
import numpy as np
import pandas as pd
from datetime import datetime

class MarketContextAnalyzer:
    """
    Analyzes and provides market context data, such as intermarket correlations.
    This analyzer works by aggregating ticks into 1-minute bars.
    """
    def __init__(self, symbols_to_monitor, correlation_window_minutes, primary_symbol):
        """
        Initializes the MarketContextAnalyzer.

        Args:
            symbols_to_monitor (list): A list of all symbols to monitor for context.
            correlation_window_minutes (int): The number of minutes for the correlation window.
            primary_symbol (str): The primary trading symbol (can be None).
        """
        self.primary_symbol = primary_symbol
        self.all_symbols = symbols_to_monitor
        self.correlation_window = correlation_window_minutes
        
        # Store minute-level close prices for each symbol
        self.minute_data = {sym: deque(maxlen=self.correlation_window) for sym in self.all_symbols}
        
        # Store the calculated correlation matrix and index
        self.correlation_matrix = pd.DataFrame()
        self.correlation_index = pd.Series(dtype=float)

        # Temp storage for building the current minute bar
        self.current_minute = None
        self.last_tick_prices = {sym: None for sym in self.all_symbols}

    def handle_tick(self, tick_data):
        """
        Processes a single tick to build minute-level bars and updates correlations.
        """
        symbol = tick_data.get('symbol')
        price = tick_data.get('ask')
        timestamp_msc = tick_data.get('timestamp_msc')

        if not all([symbol, price, timestamp_msc]):
            return

        if symbol not in self.all_symbols:
            return

        dt_object = datetime.fromtimestamp(timestamp_msc / 1000)
        self.last_tick_prices[symbol] = price

        if self.current_minute is None:
            self.current_minute = dt_object.replace(second=0, microsecond=0)

        # If a new minute has started, aggregate the last ticks into a bar
        if dt_object.minute != self.current_minute.minute:
            for sym in self.all_symbols:
                last_price = self.last_tick_prices[sym]
                if last_price is not None:
                    self.minute_data[sym].append(last_price)
            
            self.current_minute = dt_object.replace(second=0, microsecond=0)
            
            # After adding a new minute of data, recalculate correlations
            self._update_correlation_matrix()
            self._update_correlation_index()

    def _update_correlation_matrix(self):
        """
        Calculates the full correlation matrix between all monitored symbols.
        """
        # Ensure we have enough data for all symbols
        if any(len(self.minute_data[sym]) < self.correlation_window for sym in self.all_symbols):
            return

        # Create a DataFrame from the recent minute data
        df = pd.DataFrame({sym: list(self.minute_data[sym]) for sym in self.all_symbols})
        
        # Calculate the correlation matrix
        try:
            self.correlation_matrix = df.corr()
            # Handle potential NaNs if a series is flat
            self.correlation_matrix = self.correlation_matrix.fillna(0)
        except Exception:
            self.correlation_matrix = pd.DataFrame() # Reset on error

    def _update_correlation_index(self):
        """
        Calculates the average correlation for each symbol against all others.
        """
        if self.correlation_matrix.empty:
            self.correlation_index = pd.Series(dtype=float)
            return

        # Calculate the mean correlation for each symbol, excluding its correlation with itself (which is 1)
        # (sum of correlations - 1) / (number of symbols - 1)
        num_symbols = len(self.correlation_matrix)
        if num_symbols > 1:
            self.correlation_index = (self.correlation_matrix.sum() - 1) / (num_symbols - 1)
        else:
            self.correlation_index = pd.Series({self.all_symbols[0]: 0.0})


    def get_correlation_matrix(self):
        """
        Retrieves the full correlation matrix.

        Returns:
            pd.DataFrame: The correlation matrix.
        """
        return self.correlation_matrix

    def get_correlation(self, symbol_a, symbol_b):
        """
        Retrieves a specific calculated correlation between two symbols.

        Args:
            symbol_a (str): The first symbol in the pair.
            symbol_b (str): The second symbol in the pair.

        Returns:
            float or None: The correlation value, or None if not available.
        """
        if self.correlation_matrix.empty or symbol_a not in self.correlation_matrix or symbol_b not in self.correlation_matrix:
            return None
        return self.correlation_matrix.loc[symbol_a, symbol_b]

    def get_correlation_index(self, symbol):
        """
        Retrieves the correlation index for a specific symbol.

        Args:
            symbol (str): The symbol to get the index for.

        Returns:
            float or None: The correlation index value, or None if not available.
        """
        return self.correlation_index.get(symbol)

    def detect_market_regime(self, symbol, lookback_periods=100):
        """
        Detects the current market regime for a given symbol based on recent price data.

        Regimes:
        - 'Trending': High directional movement, low volatility relative to trend.
        - 'Ranging': Low volatility, price oscillating within a range.
        - 'Volatile': High volatility, erratic price movements.

        Args:
            symbol (str): The symbol to analyze.
            lookback_periods (int): Number of recent periods to analyze.

        Returns:
            str: The detected regime ('Trending', 'Ranging', 'Volatile', or 'Unknown').
        """
        if symbol not in self.minute_data or len(self.minute_data[symbol]) < lookback_periods:
            return 'Unknown'

        prices = list(self.minute_data[symbol])[-lookback_periods:]
        if len(prices) < 20:  # Need minimum data
            return 'Unknown'

        # Calculate returns
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns)

        # Simple trend strength: cumulative return over period
        cumulative_return = (prices[-1] - prices[0]) / prices[0]
        trend_strength = abs(cumulative_return)

        # ADX-like calculation (simplified)
        highs = np.maximum.accumulate(prices)
        lows = np.minimum.accumulate(prices)
        tr = np.maximum(np.abs(highs[1:] - lows[1:]), np.abs(highs[1:] - prices[:-1]), np.abs(lows[1:] - prices[:-1]))
        atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)

        # Regime logic
        if volatility > 0.001 and trend_strength > 0.005:  # High vol and strong trend
            return 'Volatile'
        elif trend_strength > 0.01:  # Strong trend
            return 'Trending'
        elif volatility < 0.0005:  # Low vol
            return 'Ranging'
        else:
            return 'Unknown'
