import pika
import json
import logging
import os
import uuid
from security_utils import decrypt_message, get_encryption_key

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
TRADE_ORDERS_QUEUE = 'trade_orders' # Standardized queue name

class OrderManager:
    """
    Manages sending order requests to the MT5 executor via RabbitMQ and tracks open positions.
    This class runs inside the Docker container.
    """
    def __init__(self):
        self.connection = None
        self.channel = None
        self.open_positions = {} # Dictionary to track open positions by a unique ID
        
        # Decrypt credentials
        encryption_key = get_encryption_key()
        encrypted_broker_user = os.getenv("ENCRYPTED_BROKER_USER")
        encrypted_broker_pass = os.getenv("ENCRYPTED_BROKER_PASS")
        
        if not all([encryption_key, encrypted_broker_user, encrypted_broker_pass]):
            logging.error("Missing environment variables for OrderManager connection.")
            return

        self.broker_user = decrypt_message(encrypted_broker_user.encode(), encryption_key)
        self.broker_pass = decrypt_message(encrypted_broker_pass.encode(), encryption_key)

        self._connect()

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

    def place_market_order(self, symbol, order_type, volume, price, stop_loss, take_profit, slippage=5, simulate=False):
        """
        Constructs and sends a market order request, and tracks the new position.
        If simulate is True, the order is tracked internally but not sent to the executor.
        """
        if simulate:
            logging.info(f"Client: SIMULATING market order: {symbol}, {order_type}, {volume} at {price} SL:{stop_loss} TP:{take_profit}")
        else:
            logging.info(f"Client: Requesting to place market order: {symbol}, {order_type}, {volume} at {price} SL:{stop_loss} TP:{take_profit}")
        
        # Generate a unique internal ID for this position
        position_id = str(uuid.uuid4())

        if not simulate:
            message = {
                "command": "place_market_order",
                "params": {
                    "internal_position_id": position_id, # Add our internal ID to the message
                    "symbol": symbol,
                    "order_type": order_type,
                    "volume": volume,
                    "price": price,
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
            "entry_price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "status": "open"
        }
        logging.info(f"OrderManager now tracking position {position_id} (Simulated: {simulate}).")

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
        logging.info(f"Position {position_id} marked as closing.")

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
        
        # Optimistically update the local state
        if new_stop_loss is not None:
            self.open_positions[position_id]['stop_loss'] = new_stop_loss
        if new_take_profit is not None:
            self.open_positions[position_id]['take_profit'] = new_take_profit
        logging.info(f"Position {position_id} modification request sent.")

    def close(self):
        """Closes the connection to RabbitMQ."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logging.info("OrderManager RabbitMQ connection closed.")
