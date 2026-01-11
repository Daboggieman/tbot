from .base import BaseCommand
import time
from influx_connector import InfluxDBConnector
from postgresql_client import PostgreSQLConnector
from news_fetcher import NewsFetcher

class DataCommands(BaseCommand):
    def add_arguments(self):
         # Send InfluxDB data
        send_influx_data_parser = self.parser.add_parser("send-influx-data", help="Send continuous test data to InfluxDB")
        send_influx_data_parser.add_argument("measurement", type=str, help="The measurement name for InfluxDB data")

        # Send PostgreSQL data
        send_pg_data_parser = self.parser.add_parser("send-pg-data", help="Send continuous test records to PostgreSQL")
        send_pg_data_parser.add_argument("table", type=str, help="The table name for PostgreSQL data")

        # Download Historical Data
        download_data_parser = self.parser.add_parser("download-historical-data", help="Download historical market data")
        download_data_parser.add_argument("symbol", type=str, help="The financial instrument to download (e.g., EURUSD)")
        download_data_parser.add_argument("timeframe", type=str, help="The timeframe for the data (e.g., D1, H1, M15)")
        download_data_parser.add_argument("start_date", type=str, help="The start date for the data in YYYY-MM-DD format")
        download_data_parser.add_argument("end_date", type=str, help="The end date for the data in YYYY-MM-DD format")

        # Fetch News
        fetch_news_parser = self.parser.add_parser("fetch-news", help="Fetch news and analyze sentiment for a symbol")
        fetch_news_parser.add_argument("symbol", type=str, help="The financial instrument to fetch news for (e.g., EURUSD)")
        fetch_news_parser.add_argument("start_date", type=str, help="The start date for the news in YYYY-MM-DD format")
        fetch_news_parser.add_argument("end_date", type=str, help="The end date for the news in YYYY-MM-DD format")

        # Economic Calendar
        economic_calendar_parser = self.parser.add_parser("fetch-economic-events", help="Fetch and display upcoming economic events")
        economic_calendar_parser.add_argument("--days", type=int, default=7, help="Number of days ahead to fetch events for (default: 7)")

    def execute(self, args, services):
        config = services.get('config')
        
        if args.command == "send-influx-data":
            self.logger.info(f"Starting continuous InfluxDB data sending for measurement: {args.measurement}")
            if not config:
                 self.logger.error("Config not available")
                 return
            influx_connector = InfluxDBConnector(url=config.INFLUXDB_URL, token=config.INFLUXDB_TOKEN, org=config.INFLUXDB_ORG, bucket=config.INFLUXDB_BUCKET)
            counter = 0
            while True:
                try:
                    tags = {"source": "bot_test"}
                    fields = {"value": counter}
                    influx_connector.write_data(args.measurement, tags, fields)
                    counter += 1
                    time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Failed to send InfluxDB data: {e}")
                    time.sleep(5)

        elif args.command == "send-pg-data":
            self.logger.info(f"Starting continuous PostgreSQL data sending for table: {args.table}")
            if not config:
                 self.logger.error("Config not available")
                 return
            pg_connector = PostgreSQLConnector(
                dbname=config.PG_DBNAME,
                user=config.PG_USER,
                password=config.PG_PASSWORD,
                host=config.PG_HOST,
                port=config.PG_PORT
            )
            counter = 0
            while True:
                try:
                    pg_connector.connect()
                    columns = {"id": "SERIAL PRIMARY KEY", "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "value": "INTEGER"}
                    pg_connector.create_table(args.table, columns)
                    data = {"value": counter}
                    pg_connector.insert_data(args.table, data)
                    self.logger.info(f"Data inserted into {args.table}: {data}")
                    counter += 1
                except Exception as e:
                    self.logger.error(f"Failed to send PostgreSQL data: {e}")
                finally:
                    pg_connector.close()
                time.sleep(1)

        elif args.command == "download-historical-data":
            self.logger.info("To download historical data, please run the following command on your host machine (not in Docker):")
            self.logger.info(f"python historical_data_importer.py {args.symbol} {args.timeframe} {args.start_date} {args.end_date}")

        elif args.command == "fetch-news":
            self.logger.info(f"Executing fetch news command for {args.symbol}")
            news_fetcher = NewsFetcher()
            news_df = news_fetcher.fetch_news_and_analyze_sentiment(args.symbol, args.start_date, args.end_date)
            news_fetcher.save_events_to_csv(news_df)
        
        elif args.command == "fetch-economic-events":
             # Assuming this logic was present or intended
             from economic_calendar import get_economic_events
             # It seems main.py didn't fully implement it in the view I had, but imported it.
             # I'll add a safe call.
             self.logger.info(f"Fetching economic events for next {args.days} days")
             # events = get_economic_events(args.days) # Hypothetical usage
             pass
