import os
import requests
import logging

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not self.bot_token or not self.chat_id:
            logging.warning("Telegram BOT_TOKEN or CHAT_ID not set. Telegram notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logging.info("Telegram Notifier initialized.")

    def send_message(self, message):
        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            logging.info(f"Telegram message sent: {message}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to send Telegram message: {e}")
