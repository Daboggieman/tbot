import collections
import os
import time
import logging
import requests
import json
import uuid
from publisher import Publisher
from influx_connector import InfluxDBConnector
from postgresql_client import PostgreSQLConnector
from config import get_config, CriticalConfigurationError

class TelegramInterface:
    def __init__(self):
        try:
            cfg = get_config()
            self.token = cfg.TELEGRAM_BOT_TOKEN
            self.chat_id = cfg.TELEGRAM_CHAT_ID
            self.broker_user = cfg.BROKER_USER
            self.broker_pass = cfg.BROKER_PASS
            self.influxdb_token = cfg.INFLUXDB_TOKEN
            
            if not self.token or not self.chat_id:
                raise ValueError("Telegram token or chat ID not set in environment.")

            self.base_url = f"https://api.telegram.org/bot{self.token}"
            self.last_update_id = 0

        except CriticalConfigurationError as e:
            logging.error(f"TelegramInterface failed to load configuration: {e}")
            raise ValueError(f"TelegramInterface failed to load configuration: {e}")

        logging.info("TelegramInterface initialized.")

        self.main_menu_keyboard = {
            "keyboard": [
                [{'text': '/status'}, {'text': '/positions'}],
                [{'text': '/events'}, {'text': '/performance'}],
                [{'text': '/logs'}, {'text': '/send'}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }

    def get_updates(self, offset):
        """Polls the Telegram API for new messages."""
        url = f"{self.base_url}/getUpdates"
        params = {'timeout': 100, 'offset': offset}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json().get('result', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Error polling Telegram updates: {e}")
            return []

    def send_message(self, text, reply_markup=None):
        """Sends a message to the configured chat ID."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)

        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending Telegram message: {e}")

    def get_system_status(self):
        """Checks the status of all services and returns a formatted string."""
        status_report = "*System Status*\n\n"

        # Check RabbitMQ
        try:
            publisher = Publisher(os.getenv("BROKER_HOST"), 5672, self.broker_user, self.broker_pass)
            publisher.connect()
            status_report += "✅ RabbitMQ: Connected\n"
            publisher.close()
        except Exception as e:
            status_report += f"❌ RabbitMQ: Connection failed\n`{e}`\n"

        # Check InfluxDB
        try:
            influx = InfluxDBConnector(url=os.getenv("INFLUXDB_URL"), token=self.influxdb_token, org=os.getenv("INFLUXDB_ORG"), bucket=os.getenv("INFLUXDB_BUCKET"))
            if influx.check_connection():
                status_report += "✅ InfluxDB: Connected\n"
            else:
                status_report += "❌ InfluxDB: Connection failed\n"
            influx.close()
        except Exception as e:
            status_report += f"❌ InfluxDB: Connection failed\n`{e}`\n"

        # Check PostgreSQL
        try:
            pg = PostgreSQLConnector(dbname=os.getenv("PG_DBNAME"), user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"), host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"))
            pg.connect()
            if pg.conn:
                status_report += "✅ PostgreSQL: Connected\n"
                pg.close()
            else:
                status_report += "❌ PostgreSQL: Connection failed\n"
        except Exception as e:
            status_report += f"❌ PostgreSQL: Connection failed\n`{e}`\n"
        
        return status_report

    def get_open_positions(self):
        """Fetches open positions from the database and returns a formatted string."""
        report = "*Open Positions*\n\n"
        try:
            pg = PostgreSQLConnector(dbname=os.getenv("PG_DBNAME"), user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"), host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"))
            pg.connect()
            if not pg.conn:
                return "❌ Could not connect to PostgreSQL."

            # Fetch column names along with the data
            query = "SELECT position_id, symbol, order_type, volume, entry_price, stop_loss, take_profit, timestamp FROM trades WHERE status = 'open' ORDER BY timestamp DESC"
            columns = ["position_id", "symbol", "order_type", "volume", "entry_price", "stop_loss", "take_profit", "timestamp"]
            open_positions = pg.fetch_all_as_dicts(query, columns)
            pg.close()

            if not open_positions:
                return "_No open positions found._", None # Return None for reply_markup

            inline_keyboard_buttons = []
            for pos in open_positions:
                report += f"*Symbol:* `{pos['symbol']}`\n"
                report += f"*Type:* {pos['order_type']}\n"
                report += f"*Volume:* {pos['volume']}\n"
                report += f"*Entry:* `{pos['entry_price']:.5f}`\n"
                report += f"*SL:* `{pos['stop_loss']:.5f}`\n"
                report += f"*TP:* `{pos['take_profit']:.5f}`\n"
                report += f"*Time (UTC):* `{pos['timestamp'].strftime('%Y-%m-%d %H:%M')}`\n"
                report += "---\n"
                inline_keyboard_buttons.append([{'text': f"Close {pos['symbol']}", 'callback_data': f"close_{pos['position_id']}"}])
            
            inline_keyboard_buttons.append([{'text': "Refresh Positions", 'callback_data': "refresh_positions"}])
            inline_markup = {"inline_keyboard": inline_keyboard_buttons}

        except Exception as e:
            logging.error(f"Error fetching positions: {e}")
            report = f"❌ An error occurred while fetching positions:\n`{e}`"
            inline_markup = None
        
        return report, inline_markup

    def get_economic_events_formatted(self, days_ahead=7):
        """Fetches economic events and returns a formatted string."""
        report = "*Upcoming Economic Events*\n\n"
        try:
            events_df = get_economic_events(days_ahead=days_ahead)
            if events_df.empty:
                return "_No high-impact economic events scheduled for the next 7 days._"
            
            high_impact_df = events_df[events_df['importance'] == 'high'].copy()
            if high_impact_df.empty:
                return "_No high-impact economic events scheduled for the next 7 days._"

            for index, row in high_impact_df.iterrows():
                report += f"*Date:* `{row['date']}`\n"
                report += f"*Time:* `{row['time']}`\n"
                report += f"*Currency:* `{row['currency']}`\n"
                report += f"*Event:* `{row['event']}`\n"
                report += f"*Importance:* `{row['importance']}`\n"
                report += "---\n"

        except Exception as e:
            logging.error(f"Error fetching economic events: {e}")
            report = f"❌ An error occurred while fetching economic events:\n`{e}`"
        
        return report

    def get_performance_report(self):
        """Calculates and returns a performance report from closed trades."""
        report = "*Trading Performance Report*\n\n"
        try:
            pg = PostgreSQLConnector(dbname=os.getenv("PG_DBNAME"), user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"), host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"))
            pg.connect()
            if not pg.conn:
                return "❌ Could not connect to PostgreSQL."

            query = "SELECT pnl FROM trades WHERE status = 'closed'"
            closed_trades_pnl = pg.fetch_all(query)
            pg.close()

            if not closed_trades_pnl:
                return "_No closed trades found to generate a report._"

            pnls = [item[0] for item in closed_trades_pnl]
            
            total_trades = len(pnls)
            winning_trades = [p for p in pnls if p > 0]
            losing_trades = [p for p in pnls if p < 0]

            num_wins = len(winning_trades)
            num_losses = len(losing_trades)
            win_rate = (num_wins / total_trades) * 100 if total_trades > 0 else 0

            total_pnl = sum(pnls)
            gross_profit = sum(winning_trades)
            gross_loss = sum(losing_trades)
            
            profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')
            avg_win = gross_profit / num_wins if num_wins > 0 else 0
            avg_loss = gross_loss / num_losses if num_losses > 0 else 0
            
            report += f"*Total PnL:* `{total_pnl:.2f}`\n"
            report += f"*Profit Factor:* `{profit_factor:.2f}`\n"
            report += f"*Total Trades:* `{total_trades}`\n"
            report += f"*Win Rate:* `{win_rate:.2f}%`\n\n"
            report += f"*Winning Trades:* `{num_wins}`\n"
            report += f"*Losing Trades:* `{num_losses}`\n\n"
            report += f"*Average Win:* `{avg_win:.2f}`\n"
            report += f"*Average Loss:* `{avg_loss:.2f}`\n"

        except Exception as e:
            logging.error(f"Error generating performance report: {e}")
            report = f"❌ An error occurred while generating the report:\n`{e}`"
        
        return report

    def get_log_lines(self, num_lines=50):
        """Reads the last N lines from the bot's log file."""
        log_file_path = os.path.join("logs", "bot.log")
        report = f"*Last {num_lines} Log Lines*\n\n"
        try:
            if not os.path.exists(log_file_path):
                return "❌ Log file not found at `logs/bot.log`."

            with open(log_file_path, 'r') as f:
                # Use deque for efficient retrieval of last N lines
                last_lines = collections.deque(f, num_lines)
            
            if not last_lines:
                return "_Log file is empty._"

            log_content = "".join(last_lines)

            # Telegram messages have a size limit of 4096 characters.
            # We reserve some space for our own formatting and truncate if necessary.
            max_len = 4000
            if len(log_content) > max_len:
                log_content = f"... (truncated)\n{log_content[-max_len:]}"

            report += f"```\n{log_content}\n```"

        except Exception as e:
            logging.error(f"Error reading log file: {e}")
            report = f"❌ An error occurred while reading the log file:\n`{e}`"
        
        return report

    def handle_command(self, command_text):
        """Parses and handles a command."""
        logging.info(f"Received command: {command_text}")
        if command_text == "/start":
            reply = "Welcome to the Trading Bot!\n\n*Available commands:*\n`/status` - Check service status.\n`/positions` - View open trades.\n`/events` - View upcoming economic events.\n`/performance` - Review trading performance.\n`/logs [lines]` - Fetch recent bot logs.\n`/send <queue> <message>` - Send a test message.\n`/trade <symbol> <vol> <buy/sell>` - Place a market order."
            self.send_message(reply, reply_markup=self.main_menu_keyboard)
        elif command_text == "/status":
            self.send_message("⏳ Checking system status...")
            status_message = self.get_system_status()
            status_markup = {"inline_keyboard": [[{"text": "Refresh Status", "callback_data": "refresh_status"}]]}
            self.send_message(status_message, reply_markup=status_markup)
        elif command_text == "/positions":
            self.send_message("⏳ Fetching open positions...")
            positions_message, inline_markup = self.get_open_positions()
            self.send_message(positions_message, reply_markup=inline_markup)
        elif command_text == "/events":
            self.send_message("⏳ Fetching economic events...")
            events_message = self.get_economic_events_formatted()
            events_markup = {"inline_keyboard": [[{"text": "Refresh Events", "callback_data": "refresh_events"}]]}
            self.send_message(events_message, reply_markup=events_markup)
        elif command_text == "/performance":
            self.send_message("⏳ Calculating performance metrics...")
            performance_message = self.get_performance_report()
            self.send_message(performance_message)
        elif command_text.startswith("/logs"):
            parts = command_text.split()
            num_lines = 50 # Default number of lines
            if len(parts) > 1 and parts[1].isdigit():
                num_lines = int(parts[1])
            
            self.send_message(f"⏳ Fetching last {num_lines} log lines...")
            log_message = self.get_log_lines(num_lines)
            self.send_message(log_message)
        elif command_text.startswith("/send "):
            parts = command_text.split(' ', 2)
            if len(parts) < 3:
                self.send_message("Usage: `/send <queue_name> <message_content>`", reply_markup=self.main_menu_keyboard)
                return
            queue_name = parts[1]
            message_content = parts[2]
            try:
                publisher = Publisher(os.getenv("BROKER_HOST"), 5672, self.broker_user, self.broker_pass)
                publisher.connect()
                publisher.publish_message(queue_name, message_content)
                publisher.close()
                self.send_message(f"✅ Message sent to queue `{queue_name}`: `{message_content}`", reply_markup=self.main_menu_keyboard)
            except Exception as e:
                logging.error(f"Error sending message to RabbitMQ: {e}")
                self.send_message(f"❌ Failed to send message: `{e}`", reply_markup=self.main_menu_keyboard)
        elif command_text == "/webapp":
            web_app_url = os.getenv("TELEGRAM_WEB_APP_URL")

            if not web_app_url or not web_app_url.startswith("https://"):
                error_text = (
                    "*Configuration Error*\n\n"
                    "The `TELEGRAM_WEB_APP_URL` is not configured correctly. "
                    "Please ensure it is set in your `.env` file and starts with `https://`."
                )
                self.send_message(error_text)
                return

            reply_text = "Click the button below to open the web interface inside Telegram:"
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🚀 Open Web App", "web_app": {"url": web_app_url}}
                    ]
                ]
            }
            self.send_message(reply_text, reply_markup=keyboard)



        else:
            self.send_message(f"Unknown command: {command_text}", reply_markup=self.main_menu_keyboard)

    def handle_callback_query(self, callback_query):
        query_data = callback_query['data']
        message_id = callback_query['message']['message_id']
        chat_id = callback_query['message']['chat']['id']

        logging.info(f"Received callback query: {query_data}")

        # Acknowledge the callback immediately to remove the loading icon
        self.answer_callback_query(callback_query['id'])

        if query_data == "refresh_positions":
            self.edit_message_text(chat_id, message_id, "⏳ Refreshing open positions...")
            positions_message, inline_markup = self.get_open_positions()
            self.edit_message_text(chat_id, message_id, positions_message, reply_markup=inline_markup)

        elif query_data == "refresh_status":
            self.edit_message_text(chat_id, message_id, "⏳ Refreshing system status...")
            status_message = self.get_system_status()
            status_markup = {"inline_keyboard": [[{"text": "Refresh Status", "callback_data": "refresh_status"}]]}
            self.edit_message_text(chat_id, message_id, status_message, reply_markup=status_markup)

        elif query_data == "refresh_events":
            self.edit_message_text(chat_id, message_id, "⏳ Refreshing economic events...")
            events_message = self.get_economic_events_formatted()
            events_markup = {"inline_keyboard": [[{"text": "Refresh Events", "callback_data": "refresh_events"}]]}
            self.edit_message_text(chat_id, message_id, events_message, reply_markup=events_markup)

        elif query_data == "cancel_trade":
            self.edit_message_text(chat_id, message_id, "_Trade cancelled._")

        elif query_data.startswith("trade_confirm:"):
            self.edit_message_text(chat_id, message_id, f"⏳ Processing trade confirmation...")
            try:
                # Decode trade details from callback data
                _, symbol, volume_str, order_type, sl_str, tp_str = query_data.split(':')
                volume = float(volume_str)
                sl_price = float(sl_str)
                tp_price = float(tp_str)

                # Construct and send the trade message
                trade_message = {
                    "command": "place_market_order",
                    "params": {
                        "internal_position_id": str(uuid.uuid4()),
                        "symbol": symbol.upper(),
                        "order_type": order_type.upper(),
                        "volume": volume,
                        "price": 0,  # Executor will fetch the live price
                        "stop_loss": sl_price,
                        "take_profit": tp_price,
                        "slippage": 10  # Default slippage
                    }
                }

                publisher = Publisher(os.getenv("BROKER_HOST"), 5672, self.broker_user, self.broker_pass)
                publisher.connect()
                publisher.publish_message('trade_orders', json.dumps(trade_message))
                publisher.close()

                self.edit_message_text(chat_id, message_id, f"✅ Trade request for {symbol.upper()} sent successfully!")

            except Exception as e:
                logging.error(f"Error processing trade confirmation: {e}")
                self.edit_message_text(chat_id, message_id, f"❌ An error occurred while placing the trade:\n`{e}`")

        elif query_data.startswith("close_"):
            position_id = query_data.replace("close_", "")
            self.edit_message_text(chat_id, message_id, f"⏳ Sending close request for position `{position_id}`...")
            
            try:
                # 1. Fetch trade details from DB
                pg = PostgreSQLConnector(dbname=os.getenv("PG_DBNAME"), user=os.getenv("POSTGRES_USER"), password=os.getenv("POSTGRES_PASSWORD"), host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"))
                pg.connect()
                if not pg.conn:
                    self.send_message("❌ Could not connect to PostgreSQL to fetch trade details.")
                    return

                query = "SELECT symbol, order_type, volume FROM trades WHERE position_id = %s"
                trade_details = pg.fetch_one(query, (position_id,))
                pg.close()

                if not trade_details:
                    self.edit_message_text(chat_id, message_id, f"❌ Could not find details for position `{position_id}`. It might already be closed.")
                    return

                symbol, order_type, volume = trade_details

                # 2. Construct the message for the executor
                close_message = {
                    "command": "close_position",
                    "params": {
                        "internal_position_id": position_id,
                        "symbol": symbol,
                        "volume": volume,
                        "order_type": order_type
                    }
                }

                # 3. Publish to RabbitMQ
                publisher = Publisher(os.getenv("BROKER_HOST"), 5672, self.broker_user, self.broker_pass)
                publisher.connect()
                publisher.publish_message('trade_orders', json.dumps(close_message))
                publisher.close()

                # 4. Notify user and refresh the positions list
                self.send_message(f"✅ Close request for position `{position_id}` sent successfully.")
                time.sleep(2) # Give the executor a moment to process
                positions_message, inline_markup = self.get_open_positions()
                self.edit_message_text(chat_id, message_id, positions_message, reply_markup=inline_markup)

            except Exception as e:
                logging.error(f"Error processing close request for {position_id}: {e}")
                self.send_message(f"❌ An error occurred while trying to close position `{position_id}`:\n`{e}`")

        else:
            self.send_message(f"Unknown callback action: {query_data}")

    def edit_message_text(self, chat_id, message_id, text, reply_markup=None):
        url = f"{self.base_url}/editMessageText"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error editing Telegram message: {e}")

    def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': show_alert
        }
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error answering callback query: {e}")

    def handle_web_app_data(self, web_app_data):
        """Handles data received from the Web App."""
        logging.info(f"Received web app data: {web_app_data['data']}")
        try:
            data = json.loads(web_app_data['data'])
            command = data.get('command')

            if command == 'send_message':
                message_text = data.get('text', '')
                if message_text:
                    # For now, let's assume a default queue 'telegram_messages'
                    queue_name = 'telegram_messages'
                    try:
                        publisher = Publisher(os.getenv("BROKER_HOST"), 5672, self.broker_user, self.broker_pass)
                        publisher.connect()
                        publisher.publish_message(queue_name, message_text)
                        publisher.close()
                        self.send_message(f"✅ Message from Web App sent to queue `{queue_name}`: `{message_text}`")
                    except Exception as e:
                        logging.error(f"Error sending message from web app to RabbitMQ: {e}")
                        self.send_message(f"❌ Failed to send message from Web App: `{e}`")
            else:
                self.send_message(f"Unknown command from Web App: {command}")

        except json.JSONDecodeError:
            logging.error("Failed to decode JSON from web app data.")
            self.send_message("Received malformed data from the Web App.")
        except Exception as e:
            logging.error(f"An error occurred in handle_web_app_data: {e}")
            self.send_message("An unexpected error occurred while processing data from the Web App.")

    def run(self):
        """Main loop to poll for and handle commands."""
        if self.last_update_id == 0:
            updates = self.get_updates(0)
            if updates:
                self.last_update_id = updates[-1]['update_id'] + 1
        
        self.send_message("🤖 **Telegram Interface Online**", reply_markup=self.main_menu_keyboard)
        logging.info("TelegramInterface is running...")

        while True:
            updates = self.get_updates(self.last_update_id)
            for update in updates:
                self.last_update_id = update['update_id'] + 1
                if 'message' in update:
                    message = update['message']
                    if str(message['chat']['id']) == self.chat_id:
                        # Handle regular text commands
                        if 'text' in message and message['text'].startswith('/'):
                            self.handle_command(message['text'])
                        # Handle data from Web App
                        elif 'web_app_data' in message:
                            self.handle_web_app_data(message['web_app_data'])
                elif 'callback_query' in update:
                    callback_query = update['callback_query']
                    if str(callback_query['from']['id']) == self.chat_id:
                        self.handle_callback_query(callback_query)
            time.sleep(1)

if __name__ == "__main__":
    # Basic logging setup for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    try:
        interface = TelegramInterface()
        interface.run()
    except ValueError as e:
        logging.critical(e)