import os
import logging
from dataclasses import dataclass
from typing import Optional
from security_utils import decrypt_message, get_encryption_key, ConfigurationError, DecryptionError

logger = logging.getLogger(__name__)

class CriticalConfigurationError(Exception):
    """Raised when the bot cannot proceed due to invalid configuration."""
    pass

@dataclass
class Config:
    # RabbitMQ
    BROKER_HOST: str
    BROKER_PORT: int
    BROKER_USER: str
    BROKER_PASS: str

    # InfluxDB
    INFLUXDB_URL: str
    INFLUXDB_TOKEN: str
    INFLUXDB_ORG: str
    INFLUXDB_BUCKET: str

    # PostgreSQL
    PG_DBNAME: str
    PG_USER: str
    PG_PASSWORD: str
    PG_HOST: str
    PG_PORT: str

    # MT5 Details (Encrypted)
    MT5_ACCOUNT: str
    MT5_PASSWORD: str
    MT5_SERVER: str

    # Options
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    @classmethod
    def load_from_env(cls):
        """Loads and validates configuration from environment variables."""
        try:
            encryption_key = get_encryption_key()
        except ConfigurationError as e:
            logger.critical(f"Configuration failed: {e}")
            raise CriticalConfigurationError(str(e))

        def get_and_decrypt(env_var, name):
            val = os.getenv(env_var)
            if not val:
                logger.warning(f"Optional environment variable missing: {env_var}. Component '{name}' will be disabled.")
                return None
            try:
                return decrypt_message(val.encode(), encryption_key)
            except DecryptionError as e:
                logger.error(f"Failed to decrypt {name}: {e}. Ensure ENCRYPTION_KEY matches.")
                return None

        try:
            config = cls(
                BROKER_HOST=os.getenv("BROKER_HOST", "rabbitmq"),
                BROKER_PORT=int(os.getenv("BROKER_PORT", 5672)),
                BROKER_USER=get_and_decrypt("ENCRYPTED_BROKER_USER", "Broker User"),
                BROKER_PASS=get_and_decrypt("ENCRYPTED_BROKER_PASS", "Broker Password"),
                
                INFLUXDB_URL=os.getenv("INFLUXDB_URL", "http://influxdb:8086"),
                INFLUXDB_TOKEN=get_and_decrypt("ENCRYPTED_INFLUXDB_TOKEN", "InfluxDB Token"),
                INFLUXDB_ORG=os.getenv("INFLUXDB_ORG", "-"),
                INFLUXDB_BUCKET=os.getenv("INFLUXDB_BUCKET", "mt5_market_data"),

                PG_DBNAME=os.getenv("PG_DBNAME", "mt5_trade_records"),
                PG_USER=os.getenv("POSTGRES_USER"),
                PG_PASSWORD=os.getenv("POSTGRES_PASSWORD"),
                PG_HOST=os.getenv("PG_HOST", "postgresql"),
                PG_PORT=os.getenv("PG_PORT", "5432"),

                MT5_ACCOUNT=get_and_decrypt("ENCRYPTED_MT5_ACCOUNT", "MT5 Account"),
                MT5_PASSWORD=get_and_decrypt("ENCRYPTED_MT5_PASSWORD", "MT5 Password"),
                MT5_SERVER=os.getenv("MT5_SERVER"),

                TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN"),
                TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
            )

            # We no longer fail here for missing credentials; 
            # instead, the specific components (LiveBroker, etc.) should check their requirements.
            return config

        except (ValueError, TypeError) as e:
            raise CriticalConfigurationError(f"Invalid configuration format: {e}")

# Global config instance for easy access
_global_config = None

def get_config():
    global _global_config
    if _global_config is None:
        _global_config = Config.load_from_env()
    return _global_config
