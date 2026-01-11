import pytest
from bot.strategies.williams_r import WilliamsRStrategy

class TestWilliamsRStrategy:
    def test_initialization(self):
        strategy = WilliamsRStrategy()
        assert strategy.window == 14
        assert strategy.buy_threshold == -80
        assert strategy.sell_threshold == -20

    def test_signal_generation(self, mock_price_data):
        strategy = WilliamsRStrategy()
        signals = strategy.generate_signals(mock_price_data)
        
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)
