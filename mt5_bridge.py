
import MetaTrader5 as mt5
import pika
import os
import time
import json
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MT5 Connection Details (assumes they are set as environment variables)
MT5_ACCOUNT = int(os.getenv('MT5_ACCOUNT', '123456'))
MT5_PASSWORD = os.getenv('MT5_PASSWORD', 'password')
MT5_SERVER = os.getenv('MT5_SERVER', 'MetaQuotes-Demo')

# RabbitMQ Connection Details
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost') # Running on host, so connect to localhost
RABBITMQ_QUEUE = 'realtime_data'
HEARTBEAT_QUEUE = 'mt5_bridge_heartbeat'
HEARTBEAT_INTERVAL = 15 # seconds

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

def connect_to_rabbitmq():
    """Establishes a connection to the RabbitMQ server."""
    logging.info(f"Connecting to RabbitMQ on host '{RABBITMQ_HOST}'...")
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        channel.queue_declare(queue=HEARTBEAT_QUEUE, durable=False) # Non-durable, short-lived queue
        logging.info("Successfully connected to RabbitMQ.")
        return channel, connection
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
        return None, None

def main():
    """Main function to run the bridge."""
    parser = argparse.ArgumentParser(description="MT5 to RabbitMQ Bridge")
    parser.add_argument("symbols", nargs='+', help="A list of symbols to subscribe to (e.g., EURUSD XAUUSD)")
    args = parser.parse_args()

    if not connect_to_mt5():
        return  # Exit if MT5 connection fails

    reconnect_delay = 5  # Initial delay in seconds

    while True:
        channel, connection = connect_to_rabbitmq()
        if channel:
            logging.info(f"Connection to RabbitMQ successful. Publishing data for {args.symbols}.")
            reconnect_delay = 5  # Reset delay after successful connection
            last_heartbeat_time = time.time()
            try:
                while True:
                    if not connection or not connection.is_open:
                        logging.warning("RabbitMQ connection lost. Attempting to reconnect...")
                        break

                    # --- Publish Price Data ---
                    for symbol in args.symbols:
                        tick = mt5.symbol_info_tick(symbol)
                        if tick:
                            tick_data = {
                                'symbol': symbol,
                                'timestamp_msc': tick.time_msc,
                                'bid': tick.bid,
                                'ask': tick.ask,
                                'last': tick.last,
                                'volume': tick.volume,
                                'flags': tick.flags
                            }
                            try:
                                channel.basic_publish(
                                    exchange='',
                                    routing_key=RABBITMQ_QUEUE,
                                    body=json.dumps(tick_data),
                                    properties=pika.BasicProperties(delivery_mode=2)
                                )
                                logging.debug(f"Published price update for {symbol}: Ask={tick.ask}")
                            except pika.exceptions.AMQPConnectionError as e:
                                logging.error(f"Failed to publish message due to connection error: {e}")
                                break # Break inner loop to trigger reconnect
                        else:
                            logging.warning(f"Could not get tick for {symbol}. Last error: {mt5.last_error()}")
                    
                    # --- Publish Heartbeat ---
                    current_time = time.time()
                    if current_time - last_heartbeat_time > HEARTBEAT_INTERVAL:
                        try:
                            heartbeat_msg = {'timestamp': current_time, 'pid': os.getpid()}
                            channel.basic_publish(
                                exchange='',
                                routing_key=HEARTBEAT_QUEUE,
                                body=json.dumps(heartbeat_msg)
                            )
                            logging.info(f"Published heartbeat.")
                            last_heartbeat_time = current_time
                        except pika.exceptions.AMQPConnectionError as e:
                            logging.error(f"Failed to publish heartbeat due to connection error: {e}")
                            break # Break inner loop to trigger reconnect

                    time.sleep(1) # Pause between each round of symbol checks

            except KeyboardInterrupt:
                logging.info("Shutdown signal received.")
                break
            except Exception as e:
                logging.error(f"An unexpected error occurred in the publishing loop: {e}")
            finally:
                if connection and connection.is_open:
                    connection.close()
                    logging.info("RabbitMQ connection closed.")
        
        else:
            logging.error(f"Failed to connect to RabbitMQ. Retrying in {reconnect_delay} seconds...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)

    mt5.shutdown()
    logging.info("MetaTrader 5 connection shut down.")

if __name__ == "__main__":
    main()
