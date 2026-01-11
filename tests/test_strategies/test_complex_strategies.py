import pytest
import pandas as pd
from bot.strategies.intermarket_aware_moving_average_crossover import IntermarketAwareMovingAverageCrossoverStrategy
from bot.strategies.arbitrage import ArbitrageStrategy
from bot.strategies.pairs_trading import PairsTradingStrategy
from bot.strategies.event_driven import EventDrivenStrategy

@pytest.fixture
def mock_secondary_data():
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'Date': dates,
        'Close': [100 + i for i in range(100)], # Simple uptrend
        'Open': [100 + i for i in range(100)],
        'High': [101 + i for i in range(100)],
        'Low': [99 + i for i in range(100)],
        'Volume': [1000] * 100,
        'tick_volume': [1000] * 100
    })
    df.set_index('Date', inplace=True)
    return df

class TestComplexStrategies:
    def test_intermarket_init(self):
        strategy = IntermarketAwareMovingAverageCrossoverStrategy()
        assert strategy.short_window == 40
        assert strategy.long_window == 100

    def test_intermarket_signals(self, mock_price_data, mock_secondary_data):
        strategy = IntermarketAwareMovingAverageCrossoverStrategy()
        signals = strategy.generate_signals(mock_price_data, mock_secondary_data)
        assert 'positions' in signals.columns

    def test_arbitrage_init(self):
        strategy = ArbitrageStrategy()
        assert strategy.threshold == 0.001

    def test_arbitrage_signals(self, mock_price_data, mock_secondary_data):
        strategy = ArbitrageStrategy()
        signals = strategy.generate_signals(mock_price_data, mock_secondary_data)
        assert 'signal_a' in signals.columns
        assert 'signal_b' in signals.columns

    def test_pairs_trading_init(self):
        strategy = PairsTradingStrategy()
        assert strategy.window == 20
        assert strategy.threshold == 1.5

    def test_pairs_trading_signals(self, mock_price_data, mock_secondary_data):
        strategy = PairsTradingStrategy()
        signals = strategy.generate_signals(mock_price_data, mock_secondary_data)
        assert 'signal_a' in signals.columns
        assert 'signal_b' in signals.columns

    def test_event_driven_init(self):
        strategy = EventDrivenStrategy()
        assert strategy.news_sentiment_threshold == 0.5

    def test_event_driven_signal(self):
        strategy = EventDrivenStrategy()
        event = {'symbol': 'EURUSD', 'type': 'news', 'sentiment': 0.8}
        signal = strategy.generate_signal(event, current_bar=10)
        assert signal['signal'] == 'BUY'
