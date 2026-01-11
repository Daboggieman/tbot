import pytest
from bot.strategies.obv import OBVStrategy
from bot.strategies.vpt import VPTStrategy

class TestVolumeStrategies:
    def test_obv_init(self):
        strategy = OBVStrategy()
        # OBV usually has no parameters, but check if there are any default
        assert isinstance(strategy, OBVStrategy)

    def test_obv_signals(self, mock_price_data):
        strategy = OBVStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)

    def test_vpt_init(self):
        strategy = VPTStrategy()
        # VPT might not have params or standard ones
        assert isinstance(strategy, VPTStrategy)

    def test_vpt_signals(self, mock_price_data):
        strategy = VPTStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)
