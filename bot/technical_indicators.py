
import pandas as pd
import numpy as np

def calculate_atr(data: pd.DataFrame, window: int = 14) -> float:
    """
    Calculates the Average True Range (ATR) for the given data.

    Args:
        data (pd.DataFrame): DataFrame with 'High', 'Low', 'Close' columns.
        window (int): The period over which to calculate the ATR.

    Returns:
        float: The latest ATR value, or 0.0 if not enough data.
    """
    if data is None or len(data) < window:
        return 0.0

    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())

    tr = np.max([high_low, high_close, low_close], axis=0)
    
    atr = pd.Series(tr).ewm(span=window, adjust=False).mean()
    
    if atr.empty:
        return 0.0
        
    return atr.iloc[-1]
