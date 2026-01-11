import pytest
import pandas as pd
import numpy as np
from bot.strategies.rsi import RSIStrategy

class TestRSIStrategy:
    def test_initialization(self):
        strategy = RSIStrategy()
        assert strategy.window == 14
        assert strategy.buy_threshold == 30
        assert strategy.sell_threshold == 70

    def test_signal_generation(self, mock_price_data):
        strategy = RSIStrategy()
        signals = strategy.generate_signals(mock_price_data)
        
        assert 'signal' in signals.columns
        assert 'positions' in signals.columns
        
        # Check signal values
        unique_signals = set(signals['positions'].dropna().unique())
        valid_values = {0.0, 1.0, -1.0, 2.0, -2.0}
        assert unique_signals.issubset(valid_values)

    def test_overbought_oversold(self):
        """Test specific price patterns that should trigger RSI signals."""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        prices = [50.0] * 50
        
        # Create a sharp drop to trigger oversold (Buy signal)
        # RSI needs a sequence of losses.
        for i in range(15, 25):
            prices[i] = prices[i-1] - 2.0 
            
        # Create a sharp rise to trigger overbought (Sell signal)
        for i in range(25, 40):
            prices[i] = prices[i-1] + 2.0
            
        df = pd.DataFrame({
            'Date': dates,
            'Close': prices,
            'Open': prices,
            'High': prices,
            'Low': prices,
            'Volume': [100] * 50
        })
        df.set_index(dates, inplace=True)
        
        strategy = RSIStrategy(window=14, buy_threshold=30, sell_threshold=70)
        signals = strategy.generate_signals(df)
        
        # We expect at least one buy signal during the drop phase (approx index 25)
        # And potentially sell signals during the rise phase (approx index 40)
        
        # Check for non-zero signals
        assert (signals['positions'] != 0).any()
