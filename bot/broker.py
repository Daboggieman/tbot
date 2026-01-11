import logging
import pika
import json
import os
from abc import ABC, abstractmethod
from security_utils import decrypt_message, get_encryption_key

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
TRADE_ORDERS_QUEUE = 'trade_orders'
MT5_REQUESTS_QUEUE = 'mt5_requests'

class Broker(ABC):
    """Abstract base class for all broker implementations."""
    @abstractmethod
    def place_order(self, symbol, order_type, volume, price, sl, tp, position_id, slippage):
        pass

    @abstractmethod
    def request_account_info(self):
        pass

class PaperBroker(Broker):
    """A simulated broker for paper trading that executes trades internally."""
    def __init__(self, initial_balance=10000):
        self.mode = 'paper'
        self.balance = initial_balance
        self.trades = []
        logging.info(f"PaperBroker initialized with balance: {self.balance}")

    def place_order(self, symbol, order_type, volume, price, sl, tp, position_id, slippage):
        logging.info(
            f"[PAPER MODE] Placing {order_type} order for position {position_id}: {volume} of {symbol} at {price:.5f}"
        )
        # In a real paper trading scenario, we would manage an open position.
        # For this abstraction, we'll just log the trade.
        logging.info(f"[PAPER MODE] Order for {symbol} recorded.")
        return True, "Order recorded in paper trading mode."

    def request_account_info(self):
        logging.info("[PAPER MODE] Account info requested. Returning simulated balance.")
        # In paper mode, we just return the current simulated balance.
        # A more complex simulation could simulate equity changes.
        return {'balance': self.balance, 'equity': self.balance}

from config import get_config

class LiveBroker(Broker):
    """A broker that sends orders to the live execution system via RabbitMQ."""
    def __init__(self):
        self.mode = 'live'
        self.connection = None
        self.channel = None
        cfg = get_config()
        self.broker_user = cfg.BROKER_USER
        self.broker_pass = cfg.BROKER_PASS
        self.rabbitmq_host = cfg.BROKER_HOST
        self._connect()

    def _connect(self):
        try:
            credentials = pika.PlainCredentials(self.broker_user, self.broker_pass)
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.rabbitmq_host, 
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=TRADE_ORDERS_QUEUE, durable=True)
            self.channel.queue_declare(queue=MT5_REQUESTS_QUEUE, durable=True)
            logging.info("LiveBroker connected to RabbitMQ.")
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"LiveBroker failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None

    def _publish(self, routing_key, message):
        if not self.channel or self.channel.is_closed:
            logging.error("Cannot publish, RabbitMQ channel not open. Reconnecting...")
            self._connect()
        
        if not self.channel:
            logging.error("Failed to reconnect to RabbitMQ. Message not sent.")
            return False

        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logging.info(f"Successfully sent message to queue '{routing_key}': {message}")
            return True
        except Exception as e:
            logging.error(f"Failed to publish message: {e}")
            return False

    def place_order(self, symbol, order_type, volume, price, sl, tp, position_id, slippage):
        logging.info(f"LiveBroker: Requesting to place market order: {order_type} {volume} {symbol}")
        message = {
            "command": "place_market_order",
            "params": {
                "internal_position_id": position_id,
                "symbol": symbol,
                "order_type": order_type.upper(),
                "volume": volume,
                "price": price,
                "stop_loss": sl,
                "take_profit": tp,
                "slippage": slippage
            }
        }
        return self._publish(TRADE_ORDERS_QUEUE, message)

    def request_account_info(self):
        logging.info("LiveBroker: Publishing request for account information.")
        message = {"command": "get_account_info"}
        self._publish(MT5_REQUESTS_QUEUE, message)
