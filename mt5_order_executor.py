import MetaTrader5 as mt5
import pika
import json
import logging
import os
import time
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

print("Executor script starting...")

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
MT5_REQUESTS_QUEUE = 'mt5_requests'
BOT_DATA_QUEUE = 'realtime_data' # Queue to send account info back to the bot

import psycopg2

# In-memory mapping of bot's internal IDs to MT5 ticket IDs
position_map = {}

def update_trade_in_db(internal_id, close_price, pnl):
    """Updates the trade status to 'closed' in the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("PG_DBNAME"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT")
        )
        cursor = conn.cursor()
        query = "UPDATE trades SET status = 'closed' WHERE position_id = %s"
        cursor.execute(query, (internal_id,))
        conn.commit()
        cursor.close()
        conn.close()
        logging.info(f"Successfully updated trade {internal_id} to closed in the database.")
    except Exception as e:
        logging.error(f"Database update for trade {internal_id} failed: {e}")

def insert_trade_in_db(internal_id, symbol, order_type, volume, entry_price, sl, tp, mt5_ticket):
    """Inserts a new trade into the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("PG_DBNAME"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT")
        )
        cursor = conn.cursor()
        query = """
            INSERT INTO trades 
            (position_id, symbol, order_type, volume, entry_price, stop_loss, take_profit, status, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'open', NOW())
        """
        cursor.execute(query, (internal_id, symbol, order_type.upper(), volume, entry_price, sl, tp))
        conn.commit()
        cursor.close()
        conn.close()
        logging.info(f"Successfully inserted new trade {internal_id} into the database.")
    except Exception as e:
        logging.error(f"Database insert for trade {internal_id} failed: {e}")

def initialize_mt5():
    """Initializes connection to the MetaTrader 5 terminal."""
    if not mt5.initialize(login=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
        logging.error(f"MT5 initialize() failed, error code = {mt5.last_error()}")
        return False
    logging.info(f"MT5 initialized successfully on account {MT5_ACCOUNT}.")
    return True

def execute_market_order(params):
    """Executes a market order and maps the internal ID to the MT5 ticket ID."""
    if not mt5.terminal_info():
        logging.warning("MT5 connection lost. Attempting to re-initialize...")
        if not initialize_mt5():
            logging.error("Failed to re-initialize MT5 connection. Order aborted.")
            return

    internal_id = params.get('internal_position_id')
    symbol = params.get('symbol')
    volume = params.get('volume')
    order_type_str = params.get('order_type')
    price = params.get('price')
    stop_loss = params.get('stop_loss')
    take_profit = params.get('take_profit')
    slippage = params.get('slippage', 5)

    if not all([internal_id, symbol, volume, order_type_str, stop_loss, take_profit]):
        logging.error("Missing required parameters for market order.")
        return

    order_type = getattr(mt5, f'ORDER_TYPE_{order_type_str.upper()}', None)
    if order_type is None:
        logging.error(f"Invalid order type: {order_type_str}")
        return

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logging.error(f"Could not retrieve tick for {symbol}. Order aborted.")
        return

    execution_price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    logging.warning(f"Overriding SL/TP from message with calculated values for testing. Original SL: {stop_loss}, TP: {take_profit}")
    if order_type == mt5.ORDER_TYPE_BUY:
        calculated_sl = round(execution_price - 0.00100, 5)
        calculated_tp = round(execution_price + 0.00100, 5)
    else: # SELL
        calculated_sl = round(execution_price + 0.00100, 5)
        calculated_tp = round(execution_price - 0.00100, 5)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": execution_price,
        "sl": calculated_sl,
        "tp": calculated_tp,
        "deviation": slippage,
        "magic": 234000,
        "comment": f"bot_{internal_id[:8]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    logging.info(f"Sending order request to MT5: {request}")
    result = mt5.order_send(request)

    if result is None:
        error_code, error_message = mt5.last_error()
        logging.error(f"order_send() failed, returned None. Last MT5 error: Code={error_code}, Message={error_message}")
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"order_send failed, retcode={result.retcode} - {result.comment}")
    else:
        logging.info(f"Market order successfully placed: {result}")
        # Persist the new trade to the database
        insert_trade_in_db(
            internal_id,
            symbol,
            order_type_str,
            volume,
            result.price, # Use the actual execution price from the result
            calculated_sl,
            calculated_tp,
            result.order # This is the MT5 ticket ID
        )
        position_map[internal_id] = result.order
        logging.info(f"Mapped internal ID {internal_id} to MT5 ticket {result.order}")

def execute_close_order(params):
    """Closes an open position using its internal ID."""
    internal_id = params.get('internal_position_id')
    symbol = params.get('symbol')
    volume = params.get('volume')
    original_order_type = params.get('order_type')

    if not all([internal_id, symbol, volume, original_order_type]):
        logging.error(f"Missing required parameters for close order: {params}")
        return

    # Fetch entry price from DB to calculate PnL later
    entry_price = None
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("PG_DBNAME"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT")
        )
        cursor = conn.cursor()
        query = "SELECT entry_price FROM trades WHERE position_id = %s"
        cursor.execute(query, (internal_id,))
        result = cursor.fetchone()
        if result:
            entry_price = result[0]
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"Database fetch for entry_price on trade {internal_id} failed: {e}")
    
    if not entry_price:
        logging.warning(f"Could not find entry price for trade {internal_id}. PnL will be inaccurate.")

    ticket_id = position_map.get(internal_id)
    if not ticket_id:
        logging.warning(f"Ticket for internal ID {internal_id} not in memory map. Searching open positions by comment...")
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            for pos in positions:
                if pos.comment == f"bot_{internal_id[:8]}":
                    ticket_id = pos.ticket
                    logging.info(f"Found ticket {ticket_id} via comment fallback for internal ID {internal_id}")
                    position_map[internal_id] = ticket_id
                    break
    
    if not ticket_id:
        logging.warning(f"Position {internal_id} not found in MT5. Assuming it's a ghost trade and marking as closed in DB for cleanup.")
        close_price_for_ghost = entry_price if entry_price is not None else 0
        update_trade_in_db(internal_id, close_price_for_ghost, 0)
        return # End of execution for this ghost trade

    close_order_type = mt5.ORDER_TYPE_SELL if original_order_type.upper() == 'BUY' else mt5.ORDER_TYPE_BUY

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        logging.error(f"Could not retrieve tick for {symbol}. Close order aborted.")
        return
    price = tick.bid if close_order_type == mt5.ORDER_TYPE_SELL else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket_id,
        "symbol": symbol,
        "volume": volume,
        "type": close_order_type,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": f"close_{internal_id[:8]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    
    logging.info(f"Sending close order request to MT5: {request}")
    result = mt5.order_send(request)

    if result is None:
        error_code, error_message = mt5.last_error()
        logging.error(f"order_send() for close failed, returned None. Last MT5 error: Code={error_code}, Message={error_message}")
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Close order failed, retcode={result.retcode} - {result.comment}")
    else:
        logging.info(f"Position {ticket_id} closed successfully: {result}")
        
        pnl = 0
        if entry_price:
            try:
                contract_size = mt5.symbol_info(symbol).trade_contract_size
                if original_order_type.upper() == 'BUY':
                    pnl = (price - entry_price) * volume * contract_size
                else: # SELL
                    pnl = (entry_price - price) * volume * contract_size
                logging.info(f"Calculated PnL for trade {internal_id}: {pnl:.2f}")
            except Exception as e:
                logging.error(f"PnL calculation for trade {internal_id} failed: {e}")

        update_trade_in_db(internal_id, price, pnl)

        if internal_id in position_map:
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

def trade_orders_callback(ch, method, properties, body):
    """Callback function to process messages from the trade orders queue."""
    logging.info(f"Received trade order: {body.decode()}")
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
            logging.warning(f"Unknown command received in trade queue: {command}")

    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON message: {body.decode()}")
    except Exception as e:
        logging.error(f"An error occurred while processing trade order: {e}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_trade_orders_consumer():
    """Starts the RabbitMQ consumer to listen for trade orders."""
    while True:
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
            channel = connection.channel()
            channel.queue_declare(queue=TRADE_ORDERS_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=TRADE_ORDERS_QUEUE, on_message_callback=trade_orders_callback)
            logging.info(f"[*] Waiting for messages on queue '{TRADE_ORDERS_QUEUE}'.")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Trade consumer RabbitMQ connection failed: {e}. Retrying in 10 seconds...")
            time.sleep(10)
        except Exception as e:
            logging.error(f"An unexpected error occurred in trade consumer: {e}. Retrying in 10 seconds...")
            time.sleep(10)

def requests_callback(ch, method, properties, body):
    """Callback for processing requests from the bot."""
    logging.info(f"Received request: {body.decode()}")
    try:
        message = json.loads(body)
        command = message.get('command')
        if command == "get_account_info":
            account_info = mt5.account_info()
            if account_info:
                response = {
                    "type": "account_info",
                    "balance": account_info.balance,
                    "equity": account_info.equity,
                    "timestamp": time.time()
                }
                ch.basic_publish(exchange='', routing_key=BOT_DATA_QUEUE, body=json.dumps(response))
                logging.info(f"Sent account info to bot: {response}")
            else:
                logging.error(f"Could not retrieve account info from MT5. Error: {mt5.last_error()}")
        else:
            logging.warning(f"Unknown command received in request queue: {command}")
    except Exception as e:
        logging.error(f"Error processing request: {e}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_requests_consumer():
    """Starts the RabbitMQ consumer to listen for requests from the bot."""
    while True:
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
            channel = connection.channel()
            channel.queue_declare(queue=MT5_REQUESTS_QUEUE, durable=True)
            channel.queue_declare(queue=BOT_DATA_QUEUE, durable=True) # Ensure response queue exists
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=MT5_REQUESTS_QUEUE, on_message_callback=requests_callback)
            logging.info(f"[*] Waiting for messages on queue '{MT5_REQUESTS_QUEUE}'.")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Request consumer RabbitMQ connection failed: {e}. Retrying in 10 seconds...")
            time.sleep(10)
        except Exception as e:
            logging.error(f"An unexpected error occurred in request consumer: {e}. Retrying in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    print("Entering main execution block...")
    if not initialize_mt5():
        exit(1)

    # Start the two consumers in separate threads
    trade_consumer_thread = Thread(target=start_trade_orders_consumer, daemon=True)
    request_consumer_thread = Thread(target=start_requests_consumer, daemon=True)
    
    trade_consumer_thread.start()
    request_consumer_thread.start()

    logging.info("All consumers started.")

    # Keep the main thread alive to handle shutdown
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        mt5.shutdown()
        logging.info("MT5 connection shut down.")
