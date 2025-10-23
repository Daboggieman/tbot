import logging
import uuid
from datetime import datetime
from postgresql_client import PostgreSQLConnector
import os
from telegram_notifier import TelegramNotifier

TRADES_TABLE = 'trades'

class OrderManager:
    """
    Manages the state of orders and positions by persisting them in a database.
    Delegates the execution of trades to a swappable broker object.
    """
    def __init__(self, broker, capital_allocator):
        self.broker = broker
        self.capital_allocator = capital_allocator
        self.open_positions = {}
        self.notifier = TelegramNotifier()
        logging.info(f"OrderManager initialized with {type(broker).__name__}.")

        try:
            self.pg_connector = PostgreSQLConnector(
                dbname=os.getenv("PG_DBNAME"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("PG_HOST"),
                port=os.getenv("PG_PORT")
            )
            self._create_trades_table_if_not_exists()
            self._load_open_positions_from_db()
        except Exception as e:
            message = f"CRITICAL: OrderManager failed to connect or set up PostgreSQL: {e}"
            logging.critical(message)
            self.notifier.send_message(f"🔥 {message}")
            self.pg_connector = None

    def request_account_info(self):
        """Requests account information by delegating to the broker."""
        return self.broker.request_account_info()

    def place_market_order(self, symbol, order_type, volume, requested_price, stop_loss, take_profit, slippage=5):
        if order_type.upper() not in ['BUY', 'SELL']:
            logging.error(f"Invalid order_type: {order_type}")
            return

        position_id = str(uuid.uuid4())

        # Delegate the actual order placement to the broker
        success, message = self.broker.place_order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=requested_price,
            sl=stop_loss,
            tp=take_profit,
            position_id=position_id,
            slippage=slippage
        )

        if success:
            position_data = {
                "position_id": position_id,
                "symbol": symbol,
                "order_type": order_type,
                "volume": volume,
                "entry_price": requested_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "status": "open"
            }
            self.open_positions[position_id] = position_data
            self._save_position_to_db(position_data)
            logging.info(f"OrderManager now tracking new position {position_id}.")
            self.notifier.send_message(f"✅ **Trade Placed** ({symbol})\nType: {order_type}\nVolume: {volume}\nPrice: {requested_price}")
        else:
            logging.error(f"OrderManager failed to place order: {message}")
            self.notifier.send_message(f"❌ **Trade Failed** ({symbol})\nReason: {message}")

    def get_open_positions(self):
        return {pid: pos for pid, pos in self.open_positions.items() if pos['status'] == 'open'}

    def close(self):
        if self.pg_connector:
            self.pg_connector.close()

    # --- Database Persistence Methods ---

    def _create_trades_table_if_not_exists(self):
        if not self.pg_connector: return
        columns = {
            "position_id": "VARCHAR(255) PRIMARY KEY",
            "symbol": "VARCHAR(255)",
            "order_type": "VARCHAR(10)",
            "volume": "FLOAT",
            "entry_price": "FLOAT",
            "stop_loss": "FLOAT",
            "take_profit": "FLOAT",
            "status": "VARCHAR(20)",
            "timestamp": "TIMESTAMP WITH TIME ZONE"
        }
        self.pg_connector.create_table(TRADES_TABLE, columns)

    def _load_open_positions_from_db(self):
        if not self.pg_connector: return
        logging.info("Loading open positions from database...")
        open_trades = self.pg_connector.fetch_data(TRADES_TABLE, "status = 'open'")
        columns = ["position_id", "symbol", "order_type", "volume", "entry_price", "stop_loss", "take_profit", "status", "timestamp"]
        for trade in open_trades:
            pos_data = dict(zip(columns, trade))
            self.open_positions[pos_data["position_id"]] = pos_data
        logging.info(f"Loaded {len(self.open_positions)} open position(s) from the database.")

    def _save_position_to_db(self, position_data):
        if not self.pg_connector: return
        pos_to_save = position_data.copy()
        pos_to_save['timestamp'] = datetime.now()
        self.pg_connector.insert_data(TRADES_TABLE, pos_to_save)

    def _update_position_in_db(self, position_id, updates):
        if not self.pg_connector: return
        updates['timestamp'] = datetime.now()
        set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
        values = list(updates.values())
        values.append(position_id)
        query = f"UPDATE {TRADES_TABLE} SET {set_clause} WHERE position_id = %s"
        self.pg_connector.execute_update(query, tuple(values))