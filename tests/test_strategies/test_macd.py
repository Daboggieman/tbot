import pytest
from bot.strategies.macd import MACDStrategy

class TestMACDStrategy:
    def test_initialization(self):
        strategy = MACDStrategy()
        assert strategy.fast_window == 12
        assert strategy.slow_window == 26
        assert strategy.signal_window == 9

    def test_signal_generation(self, mock_price_data):
        strategy = MACDStrategy()
        signals = strategy.generate_signals(mock_price_data)
        
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)
