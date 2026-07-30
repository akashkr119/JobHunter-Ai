"""Telegram notification support."""

import requests


class TelegramNotifier:
    """Send job alerts to a Telegram chat using a bot token."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, message: str) -> bool:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        response = requests.post(
            url,
            data={"chat_id": self.chat_id, "text": message},
            timeout=30,
        )
        return response.ok
