import pytest
from bot.strategies.bollinger_bands_mean_reversion import BollingerBandsMeanReversionStrategy
from bot.strategies.bollinger_bands_squeeze import BollingerBandsSqueezeStrategy

class TestBollingerBandsStrategies:
    def test_mean_reversion_init(self):
        strategy = BollingerBandsMeanReversionStrategy()
        assert strategy.window == 20
        assert strategy.num_std_dev == 2.0

    def test_mean_reversion_signals(self, mock_price_data):
        strategy = BollingerBandsMeanReversionStrategy()
        signals = strategy.generate_signals(mock_price_data)
        
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)

    def test_squeeze_init(self):
        strategy = BollingerBandsSqueezeStrategy()
        assert strategy.window == 20
        assert strategy.num_std_dev == 2.0
        assert strategy.squeeze_threshold == 2.33

    def test_squeeze_signals(self, mock_price_data):
        strategy = BollingerBandsSqueezeStrategy()
        signals = strategy.generate_signals(mock_price_data) # Squeeze logic is complex, might return few signals on random data
        
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)
