import os
import logging
from postgresql_client import PostgreSQLConnector
from security_utils import get_encryption_key, decrypt_message

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_leader_election_table():
    """
    Connects to the PostgreSQL database and creates the leader_election table.
    """
    pg_connector = None  # Initialize to None
    try:
        # --- Load database credentials from environment variables ---
        db_name = os.getenv("PG_DBNAME", "mt5_trade_records")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        host = os.getenv("PG_HOST", "postgresql")
        port = os.getenv("PG_PORT", "5432")

        if not all([db_name, user, password, host, port]):
            logging.error("Database credentials are not fully configured in environment variables.")
            return

        # --- Connect to the database ---
        pg_connector = PostgreSQLConnector(dbname=db_name, user=user, password=password, host=host, port=port)
        pg_connector.connect()

        if not pg_connector.conn:
            logging.error("Could not connect to PostgreSQL.")
            return

        # --- Define and execute the CREATE TABLE statement ---
        create_table_query = """
        CREATE TABLE IF NOT EXISTS leader_election (
            id INT PRIMARY KEY,
            leader_id VARCHAR(255) UNIQUE,
            last_heartbeat TIMESTAMP
        );
        """

        # --- Define and execute the INSERT statement ---
        insert_row_query = """
        INSERT INTO leader_election (id, leader_id, last_heartbeat)
        VALUES (1, NULL, NULL)
        ON CONFLICT (id) DO NOTHING;
        """

        with pg_connector.conn.cursor() as cur:
            logging.info("Creating leader_election table if it doesn't exist...")
            cur.execute(create_table_query)
            logging.info("Table 'leader_election' created or already exists.")

            logging.info("Inserting initial row into leader_election table...")
            cur.execute(insert_row_query)
            logging.info("Initial row inserted or already exists.")

            pg_connector.conn.commit()

        logging.info("Leader election table setup complete.")

    except Exception as e:
        logging.error(f"An error occurred during leader election table setup: {e}")
    finally:
        if pg_connector and pg_connector.conn:
            pg_connector.close()

if __name__ == "__main__":
    create_leader_election_table()
