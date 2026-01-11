import pandas as pd

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes DataFrame column names to TitleCase.
    Maps common variations like 'close', 'CLOSE' to 'Close'.
    
    Args:
        df: The input DataFrame.
        
    Returns:
        pd.DataFrame: A new DataFrame with standardized column names.
    """
    column_mapping = {
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume',
        'tick_volume': 'Volume'
    }
    
    # Create a case-insensitive map of current columns
    current_columns = {col.lower(): col for col in df.columns}
    
    new_columns = {}
    for lower_name, title_name in column_mapping.items():
        if lower_name in current_columns:
            # Only rename if the target name isn't already in the DataFrame (avoiding duplicates)
            if title_name not in df.columns or current_columns[lower_name] == title_name:
                new_columns[current_columns[lower_name]] = title_name
            
    return df.rename(columns=new_columns)
