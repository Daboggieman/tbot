import MetaTrader5 as mt5
import pandas as pd
import os
from datetime import datetime
import argparse
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MT5 Connection Details
MT5_ACCOUNT = int(os.getenv('MT5_ACCOUNT'))
MT5_PASSWORD = os.getenv('MT5_PASSWORD')
MT5_SERVER = os.getenv('MT5_SERVER')

# --- Helper Functions ---
def connect_to_mt5():
    """Initializes and connects to the MetaTrader 5 terminal."""
    logging.info("Initializing MetaTrader 5...")
    if not mt5.initialize():
        logging.error(f"initialize() failed, error code = {mt5.last_error()}")
        return False
    
    logging.info(f"Connecting to account #{MT5_ACCOUNT} on {MT5_SERVER}...")
    if not mt5.login(MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
        logging.error(f"login() failed, error code = {mt5.last_error()}")
        mt5.shutdown()
        return False
        
    logging.info("Successfully connected to MetaTrader 5.")
    return True

def main():
    """Main function to run the importer."""
    parser = argparse.ArgumentParser(description="MT5 Historical Data Importer")
    parser.add_argument("symbol", type=str, help="The financial instrument to download (e.g., EURUSD)")
    parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
    parser.add_argument("start_date", type=str, help="The start date for the data in YYYY-MM-DD format")
    parser.add_argument("end_date", type=str, help="The end date for the data in YYYY-MM-DD format")
    args = parser.parse_args()

    if not connect_to_mt5():
        return

    timeframe_mapping = {
        "D1": mt5.TIMEFRAME_D1,
        "H1": mt5.TIMEFRAME_H1,
        "M15": mt5.TIMEFRAME_M15,
        "M5": mt5.TIMEFRAME_M5,
        "M1": mt5.TIMEFRAME_M1,
    }
    mt5_timeframe = timeframe_mapping.get(args.timeframe)
    if not mt5_timeframe:
        logging.error(f"Invalid timeframe specified: {args.timeframe}")
        mt5.shutdown()
        return

    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError:
        logging.error("Invalid date format. Please use YYYY-MM-DD.")
        mt5.shutdown()
        return

    logging.info(f"Downloading historical data for {args.symbol} ({args.timeframe}) from {args.start_date} to {args.end_date}")
    rates = mt5.copy_rates_range(args.symbol, mt5_timeframe, start_date, end_date)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        logging.warning(f"No historical data found for {args.symbol} in the specified range. Creating an empty file as a placeholder.")
        data_dir = os.path.join("bot", "historical_data")
        os.makedirs(data_dir, exist_ok=True)
        filename = f"{args.symbol}_{args.timeframe}.csv"
        filepath = os.path.join(data_dir, filename)
        # Create a file with only headers. The consumer will see it's insufficient and move on.
        pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume']).to_csv(filepath, index=False)
        logging.info(f"Created empty placeholder file at {filepath}")
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'time': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'}, inplace=True)
    df.set_index('Date', inplace=True)

    data_dir = os.path.join("bot", "historical_data")
    os.makedirs(data_dir, exist_ok=True)
    filename = f"{args.symbol}_{args.timeframe}.csv"
    filepath = os.path.join(data_dir, filename)
    df.to_csv(filepath)
    logging.info(f"Historical data for {args.symbol} ({args.timeframe}) saved to {filepath}")

if __name__ == "__main__":
    main()
