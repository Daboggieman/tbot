import MetaTrader5 as mt5
import os
from dotenv import load_dotenv
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

MT5_ACCOUNT = int(os.getenv('MT5_ACCOUNT', '123456'))
MT5_PASSWORD = os.getenv('MT5_PASSWORD', 'password')
MT5_SERVER = os.getenv('MT5_SERVER', 'MetaQuotes-Demo')

def run_check():
    logging.info("Initializing MetaTrader 5...")
    if not mt5.initialize():
        logging.error(f"initialize() failed, error code = {mt5.last_error()}")
        return

    logging.info(f"Connecting to account #{MT5_ACCOUNT} on {MT5_SERVER}...")
    if not mt5.login(MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
        logging.error(f"login() failed, error code = {mt5.last_error()}")
        mt5.shutdown()
        return

    logging.info("--- Connection Successful ---")
    
    # 1. Check for the last error
    last_error = mt5.last_error()
    logging.info(f"mt5.last_error(): {last_error}")

    # 2. Request Terminal Information
    terminal_info = mt5.terminal_info()
    if terminal_info is not None:
        logging.info("mt5.terminal_info(): Successfully retrieved terminal info.")
        # Print a few key pieces of info
        logging.info(f"  - Terminal Name: {terminal_info.name}")
        logging.info(f"  - Company: {terminal_info.company}")
        logging.info(f"  - Connected: {terminal_info.connected}")
        logging.info(f"  - DLLs allowed: {terminal_info.dlls_allowed}")
    else:
        logging.error("mt5.terminal_info() failed to retrieve data.")

    # 3. Try to get data for one symbol
    symbol = "EURUSD"
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        logging.info(f"mt5.symbol_info('{symbol}'): Successfully retrieved symbol info.")
        logging.info(f"  - Price: {symbol_info.ask}")
    else:
        logging.error(f"mt5.symbol_info('{symbol}') failed. Last error: {mt5.last_error()}")

    # Shutdown connection
    mt5.shutdown()
    logging.info("--- Connection Closed ---")

if __name__ == "__main__":
    run_check()
