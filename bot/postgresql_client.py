import psycopg2
import logging
from retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)

class PostgreSQLConnector:
    def __init__(self, dbname, user, password, host, port):
        self.conn = None
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    @retry_with_backoff(allowed_exceptions=(psycopg2.Error,))
    def connect(self):
        """Establishes a connection to the PostgreSQL database."""
        # If already connected, close the old connection before creating a new one
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("Closed existing PostgreSQL connection.")

        logger.info("Attempting to connect to PostgreSQL...")
        self.conn = psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port
        )
        logger.info("Connected to PostgreSQL successfully!")

    def check_connection(self):
        """Check if the database connection is alive."""
        if not self.conn or self.conn.closed:
            return False
        try:
            # Run a simple query to check the connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except psycopg2.Error:
            return False

    def _ensure_connection(self):
        """Ensures there is an active connection to the database."""
        if not self.check_connection():
            logger.warning("Not connected to PostgreSQL or connection lost. Attempting to reconnect...")
            self.connect() # This will use the retry decorator

    def create_table(self, table_name, columns):
        try:
            self._ensure_connection()
            with self.conn.cursor() as cur:
                columns_str = ", ".join([f'{col_name} {col_type}' for col_name, col_type in columns.items()])
                cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})")
                self.conn.commit()
                logger.info(f"Table {table_name} created successfully.")
        except (psycopg2.Error, ConnectionError) as e:
            logger.error(f"Error creating table {table_name}: {e}")
            # Optionally re-raise or handle the error as needed

    def insert_data(self, table_name, data):
        try:
            self._ensure_connection()
            with self.conn.cursor() as cur:
                columns = ", ".join(data.keys())
                values = ", ".join([f"%s" for _ in data.values()])
                cur.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({values})", tuple(data.values()))
                self.conn.commit()
                logger.info(f"Data inserted into {table_name} successfully.")
        except (psycopg2.Error, ConnectionError) as e:
            logger.error(f"Error inserting data into {table_name}: {e}")

    def fetch_data(self, table_name, condition=None):
        try:
            self._ensure_connection()
            with self.conn.cursor() as cur:
                query = f"SELECT * FROM {table_name}"
                if condition:
                    query += f" WHERE {condition}"
                cur.execute(query)
                return cur.fetchall()
        except (psycopg2.Error, ConnectionError) as e:
            logger.error(f"Error fetching data from {table_name}: {e}")
            return []

    def fetch_all_as_dicts(self, query, columns):
        """Executes a SELECT query and returns results as a list of dictionaries."""
        try:
            self._ensure_connection()
            with self.conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except (psycopg2.Error, ConnectionError) as e:
            logger.error(f"Error executing custom query: {e}")
            return []

    def execute_update(self, query, params):
        """Executes an update query (e.g., UPDATE, DELETE)."""
        try:
            self._ensure_connection()
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                self.conn.commit()
                logger.info(f"Successfully executed update query. {cur.rowcount} rows affected.")
        except (psycopg2.Error, ConnectionError) as e:
            logger.error(f"Error executing update query: {e}")

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL connection closed.")
