import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def mock_price_data():
    """
    Creates a simple DataFrame mimicking OHLCV data for testing.
    Includes a clear trend to test signal generation.
    """
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    # Create a synthetic price movement
    # Uptrend then Downtrend
    prices = [100.0]
    for i in range(1, 60):
        prices.append(prices[-1] + np.random.normal(0.5, 0.2)) # Trend up
    for i in range(60, 100):
        prices.append(prices[-1] - np.random.normal(0.5, 0.2)) # Trend down
        
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices,
        'High': [p + 1.0 for p in prices],
        'Low': [p - 1.0 for p in prices],
        'Close': prices,
        'Volume': [1000] * 100,
        'tick_volume': [1000] * 100
    })
    df.set_index('Date', inplace=True)
    return df

@pytest.fixture
def empty_data():
    """Returns an empty DataFrame with the correct columns."""
    return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume', 'tick_volume'])
