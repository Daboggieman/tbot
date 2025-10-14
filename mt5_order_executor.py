import MetaTrader5 as mt5
import pika
import json
import logging
import os
import time
from threading import Thread

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MT5 Connection Details
MT5_ACCOUNT = int(os.getenv("MT5_ACCOUNT", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# RabbitMQ Connection Details
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("BROKER_USER", "guest")
RABBITMQ_PASS = os.getenv("BROKER_PASS", "guest")
TRADE_ORDERS_QUEUE = 'trade_orders'

# In-memory mapping of bot's internal IDs to MT5 ticket IDs
position_map = {}

def initialize_mt5():
    """Initializes connection to the MetaTrader 5 terminal."""
    if not mt5.initialize(login=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
        logging.error(f"MT5 initialize() failed, error code = {mt5.last_error()}")
        return False
    logging.info(f"MT5 initialized successfully on account {MT5_ACCOUNT}.")
    return True

def execute_market_order(params):
    """Executes a market order and maps the internal ID to the MT5 ticket ID."""
    internal_id = params.get('internal_position_id')
    symbol = params.get('symbol')
    volume = params.get('volume')
    order_type_str = params.get('order_type')
    price = params.get('price')
    stop_loss = params.get('stop_loss')
    take_profit = params.get('take_profit')
    slippage = params.get('slippage', 5)

    if not all([internal_id, symbol, volume, order_type_str, price, stop_loss, take_profit]):
        logging.error("Missing required parameters for market order.")
        return

    order_type = getattr(mt5, f'ORDER_TYPE_{order_type_str.upper()}', None)
    if order_type is None:
        logging.error(f"Invalid order type: {order_type_str}")
        return

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": stop_loss,
        "tp": take_profit,
        "deviation": slippage,
        "magic": 234000,
        "comment": f"bot_trade_{internal_id}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    logging.info(f"Sending order request to MT5: {request}")
    result = mt5.order_send(request)

    if result is None:
        logging.error("order_send() failed, returned None.")
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"order_send failed, retcode={result.retcode} - {result.comment}")
    else:
        logging.info(f"Market order successfully placed: {result}")
        # Map the internal ID to the real MT5 ticket ID
        position_map[internal_id] = result.order
        logging.info(f"Mapped internal ID {internal_id} to MT5 ticket {result.order}")

def execute_close_order(params):
    """Closes an open position using its internal ID."""
    internal_id = params.get('internal_position_id')
    price = params.get('price')
    symbol = params.get('symbol')
    volume = params.get('volume')
    original_order_type = params.get('order_type')

    ticket_id = position_map.get(internal_id)
    if not ticket_id:
        logging.error(f"Cannot close position: No MT5 ticket found for internal ID {internal_id}")
        return

    # Determine the correct closing order type
    close_order_type = mt5.ORDER_TYPE_SELL if original_order_type == 'BUY' else mt5.ORDER_TYPE_BUY

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket_id,
        "symbol": symbol,
        "volume": volume,
        "type": close_order_type,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": f"close bot_trade_{internal_id}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    
    logging.info(f"Sending close order request to MT5: {request}")
    result = mt5.order_send(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Close order failed, retcode={result.retcode} - {result.comment}")
    else:
        logging.info(f"Position {ticket_id} closed successfully: {result}")
        # Remove from map after closing
        del position_map[internal_id]

def execute_modify_order(params):
    """Modifies the SL/TP of an open position."""
    internal_id = params.get('internal_position_id')
    new_sl = params.get('stop_loss')
    new_tp = params.get('take_profit')

    ticket_id = position_map.get(internal_id)
    if not ticket_id:
        logging.error(f"Cannot modify position: No MT5 ticket found for internal ID {internal_id}")
        return

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket_id,
        "sl": new_sl,
        "tp": new_tp,
    }

    logging.info(f"Sending modify order request to MT5: {request}")
    result = mt5.order_modify(request)

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Modify order failed, retcode={result.retcode} - {result.comment}")
    else:
        logging.info(f"Position {ticket_id} modified successfully: {result}")

def callback(ch, method, properties, body):
    """Callback function to process messages from the queue."""
    logging.info(f"Received message: {body.decode()}")
    try:
        message = json.loads(body)
        command = message.get('command')
        params = message.get('params')

        if command == "place_market_order":
            execute_market_order(params)
        elif command == "close_position":
            execute_close_order(params)
        elif command == "modify_position":
            execute_modify_order(params)
        else:
            logging.warning(f"Unknown command received: {command}")

    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON message: {body.decode()}")
    except Exception as e:
        logging.error(f"An error occurred while processing message: {e}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    """Starts the RabbitMQ consumer to listen for trade orders."""
    while True:
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
            )
            channel = connection.channel()
            channel.queue_declare(queue=TRADE_ORDERS_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=TRADE_ORDERS_QUEUE, on_message_callback=callback)

            logging.info(f"[*] Waiting for messages on queue '{TRADE_ORDERS_QUEUE}'. To exit press CTRL+C")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ connection failed: {e}. Retrying in 10 seconds...")
            time.sleep(10)
        except Exception as e:
            logging.error(f"An unexpected error occurred in consumer: {e}. Retrying in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    if not initialize_mt5():
        exit(1)

    # Run the consumer in a separate thread
    consumer_thread = Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    # Keep the main thread alive to handle shutdown
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        mt5.shutdown()
        logging.info("MT5 connection shut down.")