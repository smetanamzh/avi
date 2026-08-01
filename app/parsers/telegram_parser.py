import logging

from telethon import TelegramClient

from app.config import API_ID, API_HASH
from app.database.repository import Repository

logger = logging.getLogger("basket")


class TelegramParser:

    def __init__(self):
        self.client = TelegramClient(
            "user_session",
            API_ID,
            API_HASH,
        )

        self.repo = Repository()

    async def parse_channel(self, channel, limit=20):

        await self.client.start()

        logger.info("Подключились к Telegram")

        count = 0

        async for message in self.client.iter_messages(
            channel,
            limit=limit,
        ):

            if not message.text:
                continue

            count += 1

            logger.info(f"Нашли сообщение {message.id}")

            self.repo.add_post(
                source="telegram",
                external_id=message.id,
                text=message.text,
            )

            logger.info("Сохранили в БД")

        logger.info(f"Всего сообщений: {count}")

        await self.client.disconnect()