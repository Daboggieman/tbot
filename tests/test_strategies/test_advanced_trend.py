import pytest
from bot.strategies.parabolic_sar import ParabolicSARStrategy
from bot.strategies.ichimoku import IchimokuStrategy
from bot.strategies.dmi_adx import DMIADXStrategy

class TestAdvancedTrendStrategies:
    def test_parabolic_sar_init(self):
        strategy = ParabolicSARStrategy()
        assert strategy.af_start == 0.02
        assert strategy.af_max == 0.2

    def test_parabolic_sar_signals(self, mock_price_data):
        strategy = ParabolicSARStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns

    def test_ichimoku_init(self):
        strategy = IchimokuStrategy()
        assert strategy.tenkan_window == 9
        assert strategy.kijun_window == 26
        assert strategy.senkou_window == 52

    def test_ichimoku_signals(self, mock_price_data):
        strategy = IchimokuStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns

    def test_dmi_adx_init(self):
        strategy = DMIADXStrategy()
        assert strategy.window == 14

    def test_dmi_adx_signals(self, mock_price_data):
        strategy = DMIADXStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
