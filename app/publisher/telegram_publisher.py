from telethon import TelegramClient

from app.config import API_ID, API_HASH, BOT_TOKEN, MY_CHANNEL_ID


class TelegramPublisher:
    def __init__(self):
        self.client = TelegramClient(
                "bot_session",
                API_ID,
                API_HASH,
        )

    async def publish(self, text: str):
        await self.client.start(bot_token=BOT_TOKEN)
        await self.client.send_message(MY_CHANNEL_ID, text)
        await self.client.disconnect()