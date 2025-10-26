import logging
import uuid
from datetime import datetime
from postgresql_client import PostgreSQLConnector
import os
from telegram_notifier import TelegramNotifier
from market_data_config import MARKET_HOURS

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

        # --- Compliance Check: Market Hours ---
        if not self.is_trading_hours_allowed(symbol):
            message = f"Compliance: Market order for {symbol} rejected. Outside defined trading hours."
            logging.warning(message)
            self.notifier.send_message(f"⚠️ {message}")
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

    def place_limit_order(self, symbol, volume, price, stop_loss, take_profit):
        # --- Compliance Check: Market Hours ---
        if not self.is_trading_hours_allowed(symbol):
            message = f"Compliance: Limit order for {symbol} rejected. Outside defined trading hours."
            logging.warning(message)
            self.notifier.send_message(f"⚠️ {message}")
            return

        position_id = str(uuid.uuid4())

        # Delegate the actual order placement to the broker
        success, message = self.broker.place_order(
            symbol=symbol,
            order_type='BUY_LIMIT' if volume > 0 else 'SELL_LIMIT', # Assuming volume sign indicates direction
            volume=abs(volume),
            price=price,
            sl=stop_loss,
            tp=take_profit,
            position_id=position_id
        )

        if success:
            position_data = {
                "position_id": position_id,
                "symbol": symbol,
                "order_type": 'BUY_LIMIT' if volume > 0 else 'SELL_LIMIT',
                "volume": abs(volume),
                "entry_price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "status": "pending" # Limit orders are pending until filled
            }
            self._save_position_to_db(position_data)
            logging.info(f"OrderManager now tracking new pending limit order {position_id}.")
            self.notifier.send_message(f"✅ **Limit Order Placed** ({symbol})\nType: {'BUY_LIMIT' if volume > 0 else 'SELL_LIMIT'}\nVolume: {abs(volume)}\nPrice: {price}")
        else:
            logging.error(f"OrderManager failed to place limit order: {message}")
            self.notifier.send_message(f"❌ **Limit Order Failed** ({symbol})\nReason: {message}")

    def place_stop_order(self, symbol, volume, price, stop_loss, take_profit):
        # --- Compliance Check: Market Hours ---
        if not self.is_trading_hours_allowed(symbol):
            message = f"Compliance: Stop order for {symbol} rejected. Outside defined trading hours."
            logging.warning(message)
            self.notifier.send_message(f"⚠️ {message}")
            return

        position_id = str(uuid.uuid4())

        # Delegate the actual order placement to the broker
        success, message = self.broker.place_order(
            symbol=symbol,
            order_type='BUY_STOP' if volume > 0 else 'SELL_STOP', # Assuming volume sign indicates direction
            volume=abs(volume),
            price=price,
            sl=stop_loss,
            tp=take_profit,
            position_id=position_id
        )

        if success:
            position_data = {
                "position_id": position_id,
                "symbol": symbol,
                "order_type": 'BUY_STOP' if volume > 0 else 'SELL_STOP',
                "volume": abs(volume),
                "entry_price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "status": "pending" # Stop orders are pending until triggered
            }
            self._save_position_to_db(position_data)
            logging.info(f"OrderManager now tracking new pending stop order {position_id}.")
            self.notifier.send_message(f"✅ **Stop Order Placed** ({symbol})\nType: {'BUY_STOP' if volume > 0 else 'SELL_STOP'}\nVolume: {abs(volume)}\nPrice: {price}")
        else:
            logging.error(f"OrderManager failed to place stop order: {message}")
            self.notifier.send_message(f"❌ **Stop Order Failed** ({symbol})\nReason: {message}")
        # --- Compliance Check: Market Hours ---
        if not self.is_trading_hours_allowed(symbol):
            message = f"Compliance: Limit order for {symbol} rejected. Outside defined trading hours."
            logging.warning(message)
            self.notifier.send_message(f"⚠️ {message}")
            return

        position_id = str(uuid.uuid4())

        # Delegate the actual order placement to the broker
        success, message = self.broker.place_order(
            symbol=symbol,
            order_type='BUY_LIMIT' if volume > 0 else 'SELL_LIMIT', # Assuming volume sign indicates direction
            volume=abs(volume),
            price=price,
            sl=stop_loss,
            tp=take_profit,
            position_id=position_id
        )

        if success:
            position_data = {
                "position_id": position_id,
                "symbol": symbol,
                "order_type": 'BUY_LIMIT' if volume > 0 else 'SELL_LIMIT',
                "volume": abs(volume),
                "entry_price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "status": "pending" # Limit orders are pending until filled
            }
            self._save_position_to_db(position_data)
            logging.info(f"OrderManager now tracking new pending limit order {position_id}.")
            self.notifier.send_message(f"✅ **Limit Order Placed** ({symbol})\nType: {'BUY_LIMIT' if volume > 0 else 'SELL_LIMIT'}\nVolume: {abs(volume)}\nPrice: {price}")
        else:
            logging.error(f"OrderManager failed to place limit order: {message}")
            self.notifier.send_message(f"❌ **Limit Order Failed** ({symbol})\nReason: {message}")

    def get_open_positions(self):
        return {pid: pos for pid, pos in self.open_positions.items() if pos['status'] == 'open'}

    def close(self):
        if self.pg_connector:
            self.pg_connector.close()

    def is_trading_hours_allowed(self, symbol, current_time=None):
        """
        Checks if trading is allowed for a given symbol at the current time (UTC).
        :param symbol: The trading symbol (e.g., 'EURUSD').
        :param current_time: Optional datetime object. If None, datetime.utcnow() is used.
        :return: True if trading is allowed, False otherwise.
        """
        if symbol not in MARKET_HOURS:
            logging.warning(f"Market hours not defined for symbol {symbol}. Assuming trading is allowed.")
            return True

        if current_time is None:
            current_time = datetime.utcnow()

        current_day_of_week = current_time.weekday() # Monday is 0, Sunday is 6
        current_hour = current_time.hour
        current_minute = current_time.minute

        allowed_intervals = MARKET_HOURS.get(symbol, [])

        for day, start_time, end_time in allowed_intervals:
            if current_day_of_week == day:
                start_hour, start_minute = start_time
                end_hour, end_minute = end_time

                # Convert current time and intervals to minutes for easier comparison
                current_total_minutes = current_hour * 60 + current_minute
                start_total_minutes = start_hour * 60 + start_minute
                end_total_minutes = end_hour * 60 + end_minute

                if start_total_minutes <= current_total_minutes <= end_total_minutes:
                    return True
        
        logging.warning(f"Trading for {symbol} is currently outside defined market hours (UTC: {current_time.strftime('%Y-%m-%d %H:%M')}).")
        return False

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