import pytest
from bot.strategies.aroon import AroonStrategy

class TestAroonStrategy:
    def test_initialization(self):
        strategy = AroonStrategy()
        assert strategy.window == 25

    def test_signal_generation(self, mock_price_data):
        strategy = AroonStrategy()
        signals = strategy.generate_signals(mock_price_data)
        
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)
