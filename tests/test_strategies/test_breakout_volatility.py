import pytest
from bot.strategies.atr_breakout import ATRBreakoutStrategy
from bot.strategies.keltner_channels import KeltnerChannelsStrategy

class TestBreakoutStrategies:
    def test_atr_breakout_init(self):
        strategy = ATRBreakoutStrategy()
        assert strategy.atr_window == 14
        assert strategy.ma_window == 20

    def test_atr_breakout_signals(self, mock_price_data):
        strategy = ATRBreakoutStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)

    def test_keltner_channels_init(self):
        strategy = KeltnerChannelsStrategy()
        assert strategy.ema_window == 20
        assert strategy.atr_window == 10

    def test_keltner_channels_signals(self, mock_price_data):
        strategy = KeltnerChannelsStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)
