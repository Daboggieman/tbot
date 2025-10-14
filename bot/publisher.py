import pika
import logging
import time

logger = logging.getLogger(__name__)

class Publisher:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None

    def connect(self, retries=5, delay=5):
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(self.host, self.port, '/', credentials)
        
        for i in range(retries):
            try:
                logger.info(f"Attempting to connect to RabbitMQ (attempt {i+1}/{retries})...")
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                logger.info("Publisher connected to RabbitMQ.")
                return
            except pika.exceptions.AMQPConnectionError as e:
                logger.error(f"RabbitMQ connection failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2 # Exponential backoff
        logger.error(f"Failed to connect to RabbitMQ after {retries} attempts.")
        raise ConnectionError("Could not connect to RabbitMQ.")

    def publish_message(self, queue_name, message):
        if not self.channel:
            logger.warning("Publisher not connected to RabbitMQ. Message not sent.")
            return
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.basic_publish(exchange='',
                                   routing_key=queue_name,
                                   body=message,
                                   properties=pika.BasicProperties(
                                       delivery_mode=2,  # make message persistent
                                   ))
        logger.info(f" [x] Sent '{message}' to queue '{queue_name}'")

    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("Publisher connection closed.")


