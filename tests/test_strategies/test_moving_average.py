import pytest
import pandas as pd
from bot.strategies.moving_average_crossover import MovingAverageCrossoverStrategy

class TestMovingAverageCrossoverStrategy:
    def test_initialization(self):
        """Test default and custom initialization."""
        strategy = MovingAverageCrossoverStrategy()
        assert strategy.short_window == 40
        assert strategy.long_window == 100

        strategy_custom = MovingAverageCrossoverStrategy(short_window=5, long_window=20)
        assert strategy_custom.short_window == 5
        assert strategy_custom.long_window == 20

    def test_signal_generation(self, mock_price_data):
        """Test that signals are generated correctly."""
        strategy = MovingAverageCrossoverStrategy(short_window=10, long_window=20)
        signals = strategy.generate_signals(mock_price_data)

        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        # Check that we have valid signals (0, 1, or -1)
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        unique_signals = set(signals['positions'].dropna().unique())
        assert unique_signals.issubset(valid_values)

    def test_insufficient_data(self, mock_price_data):
        """Test behavior with insufficient data."""
        strategy = MovingAverageCrossoverStrategy(short_window=50, long_window=100)
        # Mock data has 100 points, so short window is fine, but long window matches length
        # Let's truncate data to be very short
        short_data = mock_price_data.iloc[:40]
        
        # Depending on implementation, it might return empty signals or partial
        signals = strategy.generate_signals(short_data)
        
        # MA calculation usually produces NaNs at the start.
        # Ensure it doesn't crash.
        assert not signals.empty
