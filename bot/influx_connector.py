import logging
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException
from retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)

class InfluxDBConnector:
    def __init__(self, url, token, org, bucket):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None
        self.connect()

    @retry_with_backoff(allowed_exceptions=(ApiException, ConnectionError))
    def connect(self):
        """Initializes the InfluxDB client and write API."""
        logger.info("Attempting to connect to InfluxDB...")
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        if not self.check_connection():
            raise ConnectionError("InfluxDB connection check failed after initialization.")
        logger.info("Connected to InfluxDB successfully!")

    def check_connection(self):
        """Check if the database connection is alive."""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except Exception as e:
            logger.warning(f"InfluxDB ping failed: {e}")
            return False

    def _ensure_connection(self):
        """Ensures there is an active connection to the database."""
        if not self.check_connection():
            logger.warning("Not connected to InfluxDB or connection lost. Attempting to reconnect...")
            self.connect() # This will use the retry decorator

    @retry_with_backoff(allowed_exceptions=(ApiException, ConnectionError))
    def write_data(self, measurement, tags, fields):
        """Writes a single data point to InfluxDB with retry logic."""
        self._ensure_connection()
        point = Point(measurement)
        for key, value in tags.items():
            point = point.tag(key, value)
        for key, value in fields.items():
            point = point.field(key, value)
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        logger.debug(f"Data written to InfluxDB: {measurement}")

    @retry_with_backoff(allowed_exceptions=(ApiException, ConnectionError))
    def query_data(self, query):
        """Queries data from InfluxDB with retry logic."""
        self._ensure_connection()
        query_api = self.client.query_api()
        tables = query_api.query(query, org=self.org)
        results = []
        for table in tables:
            for record in table.records:
                results.append(record.values)
        return results

    def close(self):
        if self.client:
            self.client.close()
            logger.info("InfluxDB client closed.")
