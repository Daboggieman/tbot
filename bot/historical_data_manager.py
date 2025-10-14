import logging
import pandas as pd
import os

class HistoricalDataManager:
    def __init__(self, data_dir="historical_data"):
        """Initializes the HistoricalDataManager."""
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        logging.info("HistoricalDataManager initialized.")

    def load_data_from_csv(self, symbol, timeframe):
        """
        Loads historical data from a CSV file.
        """
        filename = f"{symbol}_{timeframe}.csv"
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            logging.warning(f"Historical data file not found: {filepath}")
            return None
        df = pd.read_csv(filepath, index_col='Date', parse_dates=True)
        logging.info(f"Loaded {len(df)} records from {filepath}")
        return df