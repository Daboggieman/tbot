from .base import BaseCommand
from publisher import Publisher
from influx_connector import InfluxDBConnector
from postgresql_client import PostgreSQLConnector
import time

class SystemCommands(BaseCommand):
    def add_arguments(self):
        # Status
        self.parser.add_parser("status", help="Check the status of bot services")

        # Send Message
        send_message_parser = self.parser.add_parser("send-message", help="Send a test message via RabbitMQ")
        send_message_parser.add_argument("message", type=str, help="The message to send")
        send_message_parser.add_argument("--loop", action="store_true", help="Continuously send messages for testing retry mechanism")

        # Crash
        self.parser.add_parser("crash", help="Intentionally crash the bot for testing restart policy")

        # Start Web
        self.parser.add_parser("start-web", help="Start the web interface")

        # Start Telegram Interface
        self.parser.add_parser("start-telegram-interface", help="Start the Telegram command interface")

        # Start Trading Session
        start_trading_session_parser = self.parser.add_parser("start-trading-session", help="Start a dynamic real-time trading session using the StrategySelector.")
        start_trading_session_parser.add_argument("symbol", type=str, help="The primary symbol to trade (e.g., EURUSD)")
        start_trading_session_parser.add_argument("--secondary-symbol", type=str, help="An optional secondary symbol for intermarket analysis.")
        start_trading_session_parser.add_argument("--correlation-window-minutes", type=int, help="The correlation window in minutes (e.g., 60). Required if --secondary-symbol is used.")
        start_trading_session_parser.add_argument("--quiet-period-before-minutes", type=int, default=30, help="Minutes before a high-impact event to pause trading (default: 30).")
        start_trading_session_parser.add_argument("--quiet-period-after-minutes", type=int, default=5, help="Minutes after a high-impact event to resume trading (default: 5).")
        start_trading_session_parser.add_argument("--candle-interval-minutes", type=int, default=1, help="The interval in minutes for aggregating ticks into candles (default: 1)")
        start_trading_session_parser.add_argument("--mode", type=str, choices=['live', 'paper'], default='paper', help="The trading mode: 'live' for real trading, 'paper' for simulated trading (default: paper)")


    def execute(self, args, services):
        config = services.get('config')
        
        if args.command == "status":
            self.logger.info("Checking bot service status...")
            if not config:
                 self.logger.error("Config not available")
                 return
            
            # Check RabbitMQ connection
            try:
                publisher = Publisher(config.BROKER_HOST, config.BROKER_PORT, config.BROKER_USER, config.BROKER_PASS)
                publisher.connect()
                self.logger.info("RabbitMQ: Connected")
                publisher.close()
            except Exception as e:
                self.logger.error(f"RabbitMQ: Connection failed - {e}")

            # Check InfluxDB connection
            try:
                influx_connector = InfluxDBConnector(url=config.INFLUXDB_URL, token=config.INFLUXDB_TOKEN, org=config.INFLUXDB_ORG, bucket=config.INFLUXDB_BUCKET)
                influx_connector.write_data(measurement="status_check", tags={"service": "bot"}, fields={"status": 1})
                self.logger.info("InfluxDB: Connected and writable")
                influx_connector.close()
            except Exception as e:
                 self.logger.error(f"InfluxDB: Connection failed - {e}")

            # Check PostgreSQL connection
            try:
                pg_connector = PostgreSQLConnector(
                    dbname=config.PG_DBNAME,
                    user=config.PG_USER,
                    password=config.PG_PASSWORD,
                    host=config.PG_HOST,
                    port=config.PG_PORT
                )
                pg_connector.connect()
                if pg_connector.conn:
                    self.logger.info("PostgreSQL: Connected")
                    pg_connector.close()
                else:
                    self.logger.error("PostgreSQL: Connection failed")
            except Exception as e:
                 self.logger.error(f"PostgreSQL: Connection failed - {e}")

        elif args.command == "send-message":
            if not config:
                 self.logger.error("Config not available")
                 return
            
            if args.loop:
                self.logger.info(f"Starting continuous message sending loop with message: {args.message}")
                publisher = Publisher(config.BROKER_HOST, config.BROKER_PORT, config.BROKER_USER, config.BROKER_PASS)
                while True:
                    try:
                        publisher.connect()
                        publisher.publish_message("test_queue", args.message)
                        # MESSAGES_SENT.inc() # Re-implement metrics if needed, or pass as service
                        self.logger.info("Message sent successfully.")
                    except Exception as e:
                        self.logger.error(f"Failed to send message: {e}")
                    time.sleep(2)
            else:
                self.logger.info(f"Sending message: {args.message}")
                try:
                    publisher = Publisher(config.BROKER_HOST, config.BROKER_PORT, config.BROKER_USER, config.BROKER_PASS)
                    publisher.connect()
                    publisher.publish_message("test_queue", args.message)
                    publisher.publish_message("realtime_data", args.message)
                    self.logger.info("Message sent successfully to both queues.")
                    publisher.close()
                except Exception as e:
                    self.logger.error(f"Failed to send message: {e}")
        
        elif args.command == "start-web":
            self.logger.info("Starting web interface...")
            from web_interface import app
            app.run(host='0.0.0.0', port=5000)
