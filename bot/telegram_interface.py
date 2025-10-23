import os
import time
import logging
import requests
import json
from publisher import Publisher
from influx_connector import InfluxDBConnector
from postgresql_client import PostgreSQLConnector
from security_utils import decrypt_message, get_encryption_key
from economic_calendar import get_economic_events

class TelegramInterface:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0

        if not self.token or not self.chat_id:
            logging.error("TelegramInterface: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
            raise ValueError("Telegram token or chat ID not set in environment.")
        
        # --- Load and decrypt credentials ---
        try:
            encryption_key = get_encryption_key()
            self.broker_user = decrypt_message(os.getenv("ENCRYPTED_BROKER_USER").encode(), encryption_key)
            self.broker_pass = decrypt_message(os.getenv("ENCRYPTED_BROKER_PASS").encode(), encryption_key)
            self.influxdb_token = decrypt_message(os.getenv("ENCRYPTED_INFLUXDB_TOKEN").encode(), encryption_key)
        except Exception as e:
            logging.error(f"TelegramInterface failed to load or decrypt credentials: {e}")
            raise ValueError(f"TelegramInterface failed to load or decrypt credentials: {e}")

        logging.info("TelegramInterface initialized.")

        self.main_menu_keyboard = {
            "keyboard": [
                [{'text': '/status'}],
                [{'text': '/positions'}],
                [{'text': '/events'}],
                [{'text': '/send'}]
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

    def handle_command(self, command_text):
        """Parses and handles a command."""
        logging.info(f"Received command: {command_text}")
        if command_text == "/start":
            reply = "Welcome to the Trading Bot!\n\n*Available commands:*\n`/status` - Check service status.\n`/positions` - View open trades.\n`/events` - View upcoming economic events.\n`/send <queue> <message>` - Send a test message to a RabbitMQ queue."
            self.send_message(reply, reply_markup=self.main_menu_keyboard)
        elif command_text == "/status":
            self.send_message("⏳ Checking system status...")
            status_message = self.get_system_status()
            self.send_message(status_message, reply_markup=self.main_menu_keyboard)
        elif command_text == "/positions":
            self.send_message("⏳ Fetching open positions...")
            positions_message, inline_markup = self.get_open_positions()
            self.send_message(positions_message, reply_markup=inline_markup)
        elif command_text == "/events":
            self.send_message("⏳ Fetching economic events...")
            events_message = self.get_economic_events_formatted()
            self.send_message(events_message, reply_markup=self.main_menu_keyboard)
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
        else:
            self.send_message(f"Unknown command: {command_text}", reply_markup=self.main_menu_keyboard)

    def handle_callback_query(self, callback_query):
        query_data = callback_query['data']
        message_id = callback_query['message']['message_id']
        chat_id = callback_query['message']['chat']['id']

        logging.info(f"Received callback query: {query_data}")

        if query_data == "refresh_positions":
            self.send_message("⏳ Refreshing open positions...", chat_id=chat_id)
            positions_message, inline_markup = self.get_open_positions()
            self.edit_message_text(chat_id, message_id, positions_message, reply_markup=inline_markup)
        elif query_data.startswith("close_"):
            position_id = query_data.replace("close_", "")
            self.send_message(f"Closing position `{position_id}`... (Not implemented yet)", chat_id=chat_id)
            # Here you would add logic to actually close the position
            # For now, just acknowledge and refresh
            positions_message, inline_markup = self.get_open_positions()
            self.edit_message_text(chat_id, message_id, positions_message, reply_markup=inline_markup)
        else:
            self.send_message(f"Unknown callback action: {query_data}", chat_id=chat_id)

        # Always answer the callback query to remove the loading animation on the button
        self.answer_callback_query(callback_query['id'])

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
                if 'message' in update and 'text' in update['message']:
                    message = update['message']
                    # Only process messages from the configured user
                    if str(message['chat']['id']) == self.chat_id:
                        text = message['text']
                        if text.startswith('/'):
                            self.handle_command(text)
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