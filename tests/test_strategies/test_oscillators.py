import pytest
from bot.strategies.stochastic_oscillator import StochasticOscillatorStrategy
from bot.strategies.cci import CCIStrategy
from bot.strategies.roc import ROCStrategy
from bot.strategies.momentum import MomentumStrategy

class TestOscillatorStrategies:
    def test_stochastic_init(self):
        strategy = StochasticOscillatorStrategy()
        assert strategy.k_window == 14
        assert strategy.d_window == 3

    def test_stochastic_signals(self, mock_price_data):
        strategy = StochasticOscillatorStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)

    def test_cci_init(self):
        strategy = CCIStrategy()
        assert strategy.window == 20

    def test_cci_signals(self, mock_price_data):
        strategy = CCIStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)

    def test_roc_init(self):
        strategy = ROCStrategy()
        assert strategy.window == 12

    def test_roc_signals(self, mock_price_data):
        strategy = ROCStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)

    def test_momentum_init(self):
        strategy = MomentumStrategy()
        assert strategy.window == 14

    def test_momentum_signals(self, mock_price_data):
        strategy = MomentumStrategy()
        signals = strategy.generate_signals(mock_price_data)
        assert 'signal' in signals.columns
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)
