import pandas as pd
import numpy as np

def add_all_indicators(data: pd.DataFrame):
    """
    Adds a comprehensive set of technical indicators to the DataFrame.
    """
    data['SMA_10'] = data['Close'].rolling(window=10).mean()
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['EMA_12'] = data['Close'].ewm(span=12, adjust=False).mean()
    data['EMA_26'] = data['Close'].ewm(span=26, adjust=False).mean()
    
    # RSI
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()

    # Handle division by zero
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rs.ffill(inplace=True)

    data['RSI'] = 100 - (100 / (1 + rs))
    data['RSI'] = data['RSI'].fillna(50) # Fill initial NaNs with a neutral 50

    # MACD
    data['MACD'] = data['EMA_12'] - data['EMA_26']
    data['MACD_signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

    # ATR (more robust calculation)
    tr_df = pd.DataFrame(index=data.index)
    tr_df['h-l'] = data['High'] - data['Low']
    tr_df['h-pc'] = abs(data['High'] - data['Close'].shift(1))
    tr_df['l-pc'] = abs(data['Low'] - data['Close'].shift(1))
    
    true_range = tr_df.max(axis=1)
    data['ATR'] = true_range.ewm(span=14, adjust=False).mean()
    
    data.dropna(inplace=True)
    return data

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

    tr_df = pd.DataFrame(index=data.index)
    tr_df['h-l'] = data['High'] - data['Low']
    tr_df['h-pc'] = abs(data['High'] - data['Close'].shift(1))
    tr_df['l-pc'] = abs(data['Low'] - data['Close'].shift(1))
    
    true_range = tr_df.max(axis=1)
    atr = true_range.ewm(span=window, adjust=False).mean()
    
    if atr.empty:
        return 0.0
        
    return atr.iloc[-1]