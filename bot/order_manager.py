import pika
import json
import logging
import os
import uuid
from datetime import datetime
from security_utils import decrypt_message, get_encryption_key
from postgresql_client import PostgreSQLConnector

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
TRADE_ORDERS_QUEUE = 'trade_orders' # Standardized queue name
TRADES_TABLE = 'trades'

class OrderManager:
    """
    Manages sending order requests to the MT5 executor via RabbitMQ and tracks open positions
    by persisting them in a PostgreSQL database.
    This class runs inside the Docker container.
    """
    def __init__(self):
        self.connection = None
        self.channel = None
        self.open_positions = {} # In-memory cache of open positions

        # Decrypt RabbitMQ credentials
        try:
            encryption_key_str = get_encryption_key()
            encryption_key_bytes = encryption_key_str.encode()
            encrypted_broker_user = os.getenv("ENCRYPTED_BROKER_USER")
            encrypted_broker_pass = os.getenv("ENCRYPTED_BROKER_PASS")
            
            if not all([encryption_key_str, encrypted_broker_user, encrypted_broker_pass]):
                raise ValueError("Missing environment variables for RabbitMQ connection.")

            self.broker_user = decrypt_message(encrypted_broker_user.encode(), encryption_key_bytes)
            self.broker_pass = decrypt_message(encrypted_broker_pass.encode(), encryption_key_bytes)
        except Exception as e:
            logging.critical(f"OrderManager failed to decrypt RabbitMQ credentials: {e}")
            raise

        self._connect()

        # --- PostgreSQL Integration ---
        try:
            self.pg_connector = PostgreSQLConnector(
                dbname=os.getenv("PG_DBNAME"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("PG_HOST"),
                port=os.getenv("PG_PORT")
            )
            self._create_trades_table_if_not_exists()
            self._load_open_positions_from_db()
        except Exception as e:
            logging.critical(f"OrderManager failed to connect or set up PostgreSQL: {e}")
            self.pg_connector = None
        # --------------------------

    def _connect(self):
        """Establishes a connection and channel to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(self.broker_user, self.broker_pass)
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=TRADE_ORDERS_QUEUE, durable=True)
            logging.info("OrderManager connected to RabbitMQ successfully.")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None

    def _publish(self, message):
        """Publishes a message to the trade orders queue."""
        if not self.channel or self.channel.is_closed:
            logging.error("Cannot publish message, RabbitMQ channel is not open. Reconnecting...")
            self._connect()
        
        if not self.channel:
            logging.error("Failed to reconnect to RabbitMQ. Message not sent.")
            return

        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=TRADE_ORDERS_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                ))
            logging.info(f"Successfully sent message to queue '{TRADE_ORDERS_QUEUE}': {message}")
        except Exception as e:
            logging.error(f"Failed to publish message: {e}")

    def place_market_order(self, symbol, order_type, volume, requested_price, stop_loss, take_profit, slippage=5, simulate=False):
        """
        Constructs and sends a market order request, and tracks the new position.
        If simulate is True, the order is tracked internally but not sent to the executor.
        """
        if order_type.upper() not in ['BUY', 'SELL']:
            logging.error(f"Invalid order_type: {order_type}. Must be 'BUY' or 'SELL'.")
            return

        if simulate:
            logging.info(f"Client: SIMULATING market order: {order_type} {volume} {symbol} at {requested_price} SL:{stop_loss} TP:{take_profit}")
        else:
            logging.info(f"Client: Requesting to place market order: {order_type} {volume} {symbol} at {requested_price} SL:{stop_loss} TP:{take_profit}")
        
        # Generate a unique internal ID for this position
        position_id = str(uuid.uuid4())

        if not simulate:
            message = {
                "command": "place_market_order",
                "params": {
                    "internal_position_id": position_id, # Add our internal ID to the message
                    "symbol": symbol,
                    "order_type": order_type.upper(), # Executor expects 'BUY' or 'SELL'
                    "volume": volume,
                    "price": requested_price, # The price for execution deviation check
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "slippage": slippage
                }
            }
            self._publish(message)
        else:
            logging.info(f"OrderManager: Simulated order {position_id} not published to RabbitMQ.")

        # NOTE: In a real system, we would wait for a confirmation from the executor
        # with the real ticket ID. For now, we optimistically track it.
        self.open_positions[position_id] = {
            "position_id": position_id,
            "symbol": symbol,
            "order_type": order_type,
            "volume": volume,
            "entry_price": requested_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "status": "open"
        }
        logging.info(f"OrderManager now tracking position {position_id} (Simulated: {simulate}).")
        if not simulate:
            self._save_position_to_db(self.open_positions[position_id])

    def get_open_positions(self):
        """Returns a dictionary of all open positions."""
        return {pid: pos for pid, pos in self.open_positions.items() if pos['status'] == 'open'}

    def close_position(self, position_id, price):
        """Constructs and sends a close order request."""
        if position_id not in self.open_positions or self.open_positions[position_id]['status'] != 'open':
            logging.warning(f"Attempted to close an invalid or already closing position {position_id}")
            return

        pos = self.open_positions[position_id]
        logging.info(f"Client: Requesting to close position {position_id} ({pos['symbol']}) at price {price}")
        message = {
            "command": "close_position",
            "params": {
                "internal_position_id": position_id,
                "symbol": pos['symbol'],
                "volume": pos['volume'],
                "order_type": pos['order_type'],
                "price": price
            }
        }
        self._publish(message)
        self.open_positions[position_id]['status'] = 'closing' # Mark as closing to prevent duplicate orders
        self._update_position_in_db(position_id, {'status': 'closing'})
        logging.info(f"Position {position_id} marked as closing in memory and database.")

    def modify_position(self, position_id, new_stop_loss=None, new_take_profit=None):
        """Constructs and sends a modify order request."""
        if position_id not in self.open_positions or self.open_positions[position_id]['status'] != 'open':
            logging.warning(f"Attempted to modify an invalid or closing position {position_id}")
            return

        pos = self.open_positions[position_id]
        logging.info(f"Client: Requesting to modify position {position_id} ({pos['symbol']}) with SL: {new_stop_loss} TP: {new_take_profit}")
        message = {
            "command": "modify_position",
            "params": {
                "internal_position_id": position_id,
                "symbol": pos['symbol'],
                "stop_loss": new_stop_loss,
                "take_profit": new_take_profit
            }
        }
        self._publish(message)
        
        updates = {}
        if new_stop_loss is not None:
            self.open_positions[position_id]['stop_loss'] = new_stop_loss
            updates['stop_loss'] = new_stop_loss
        if new_take_profit is not None:
            self.open_positions[position_id]['take_profit'] = new_take_profit
            updates['take_profit'] = new_take_profit
        
        if updates:
            self._update_position_in_db(position_id, updates)

        logging.info(f"Position {position_id} modification request sent.")

    def close(self):
        """Closes the connection to RabbitMQ and PostgreSQL."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.info("OrderManager RabbitMQ connection closed.")
        if self.pg_connector:
            self.pg_connector.close()

    # --- Database Persistence Methods ---

    def _create_trades_table_if_not_exists(self):
        """Creates the 'trades' table in the database if it doesn't already exist."""
        if not self.pg_connector: return
        
        columns = {
            "position_id": "VARCHAR(255) PRIMARY KEY",
            "symbol": "VARCHAR(255)",
            "order_type": "VARCHAR(10)",
            "volume": "FLOAT",
            "entry_price": "FLOAT",
            "stop_loss": "FLOAT",
            "take_profit": "FLOAT",
            "status": "VARCHAR(20)",
            "timestamp": "TIMESTAMP WITH TIME ZONE"
        }
        self.pg_connector.create_table(TRADES_TABLE, columns)

    def _load_open_positions_from_db(self):
        """Loads all 'open' positions from the database into the in-memory dictionary."""
        if not self.pg_connector: return

        logging.info("Loading open positions from database...")
        open_trades = self.pg_connector.fetch_data(TRADES_TABLE, "status = 'open'")
        
        # Define the order of columns as they are in the database schema
        columns = ["position_id", "symbol", "order_type", "volume", "entry_price", "stop_loss", "take_profit", "status", "timestamp"]

        for trade in open_trades:
            pos_data = dict(zip(columns, trade))
            position_id = pos_data["position_id"]
            self.open_positions[position_id] = pos_data
        
        logging.info(f"Loaded {len(self.open_positions)} open position(s) from the database.")

    def _save_position_to_db(self, position_data):
        """Saves a new position to the trades table."""
        if not self.pg_connector: return
        
        pos_to_save = position_data.copy()
        pos_to_save['timestamp'] = datetime.now()
        self.pg_connector.insert_data(TRADES_TABLE, pos_to_save)

    def _update_position_in_db(self, position_id, updates):
        """Updates an existing position in the trades table."""
        if not self.pg_connector: return

        updates['timestamp'] = datetime.now()
        set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
        values = list(updates.values())
        values.append(position_id)
        
        query = f"UPDATE {TRADES_TABLE} SET {set_clause} WHERE position_id = %s"
        self.pg_connector.execute_update(query, tuple(values))
