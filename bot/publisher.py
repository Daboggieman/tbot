import pika
import logging
import time
from retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)

class Publisher:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None
        self._credentials = pika.PlainCredentials(self.username, self.password)
        self._parameters = pika.ConnectionParameters(
            host=self.host, 
            port=self.port, 
            virtual_host='/', 
            credentials=self._credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )

    @retry_with_backoff(retries=10, initial_delay=2, backoff_factor=2, allowed_exceptions=(pika.exceptions.AMQPConnectionError,))
    def connect(self):
        """Connects to RabbitMQ with retry and backoff."""
        if self.connection and not self.connection.is_closed:
            return

        logger.info(f"Connecting to RabbitMQ at {self.host}:{self.port}...")
        self.connection = pika.BlockingConnection(self._parameters)
        self.channel = self.connection.channel()
        logger.info("Publisher connected to RabbitMQ.")

    def publish_message(self, queue_name, message):
        """Publishes a message, attempting to reconnect if the connection is lost."""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            
            self.channel.queue_declare(queue=queue_name, durable=True)
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                )
            )
            logger.info(f"Sent message to {queue_name}")
        except (pika.exceptions.AMQPError, ConnectionError) as e:
            logger.error(f"Failed to publish message: {e}. Attempting recovery on next call.")
            # Ensure connection is marked as closed for next attempt
            if self.connection and not self.connection.is_closed:
                self.connection.close()

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Publisher connection closed.")


