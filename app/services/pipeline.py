import asyncio
import logging
import re
from datetime import datetime

from app.ai.client import AIClient
from app.config import (
    CHANNEL_IDS,
    PUBLISH_INTERVAL_MINUTES,
    PUBLISH_START_HOUR,
    PUBLISH_END_HOUR,
    RESET_DB,
    VK_TOKEN,
    VK_GROUP_IDS,
)
from app.database.repository import Repository
from app.parsers.telegram_parser import TelegramParser
from app.parsers.vk_parser import VKParser
from app.publisher.telegram_publisher import TelegramPublisher

logger = logging.getLogger("basket")


class Pipeline:

    def __init__(self):
        self.repo = Repository()
        self.ai = AIClient()
        self.parser = TelegramParser()
        self.vk_parser = VKParser()
        self.publisher = TelegramPublisher()
        self._last_publish: datetime | None = None

    async def run(self):
        if RESET_DB:
            self.repo.reset_db()
        else:
            self.repo.reset_analysis()

        await self._cycle()

    async def run_forever(self, cycle_minutes: int = 6):
        if RESET_DB:
            self.repo.reset_db()
        else:
            self.repo.reset_analysis()

        logger.info(f"Запущен автономный режим, цикл каждые {cycle_minutes} мин")
        while True:
            await self._cycle()
            logger.info(f"Сплю {cycle_minutes} мин...")
            await asyncio.sleep(cycle_minutes * 60)

    async def _cycle(self):
        await self._parse_all()
        await self._process_posts()
        await self._publish_scheduled()

    async def _parse_all(self):
        logger.info("Парсим источники...")

        # Telegram парсер отключён
        logger.info("Telegram парсер отключён, пропускаем")
        # for channel in CHANNEL_IDS:
        #     logger.info(f"--- {channel} ---")
        #     await self.parser.parse_channel(channel, limit=500)

        if VK_TOKEN and VK_GROUP_IDS:
            await self.vk_parser.parse_groups(limit=200)
        else:
            logger.info("VK пропущен (VK_TOKEN или VK_GROUP_IDS пусты)")

        logger.info("Готово.")

    async def _process_posts(self):
        posts = self.repo.get_unprocessed_posts(limit=50)
        logger.info(f"Новых сообщений: {len(posts)}")
        if not posts:
            return

        history = self.repo.get_all_rewritten_texts()
        sem = asyncio.Semaphore(3)

        async def process(post):
            async with sem:
                return post, await self.ai.analyze(post.text, history)

        results = await asyncio.gather(*[process(p) for p in posts])

        for idx, (post, result) in enumerate(results, 1):
            logger.info(f"Обрабатываем: {idx}/{len(posts)} | vk:{post.id}")
            _preview = post.text[:200].replace('\n', ' ').strip()
            logger.info(f"  └ Текст: {_preview}...")

            if not result["accept"]:
                reason = result.get('_skip_reason', 'unknown')
                logger.info(f"  └ SKIP ({reason})")
                self.repo.mark_skipped(post)
                continue

            if result["duplicate"]:
                logger.info("  └ Дубликат")
                self.repo.mark_duplicate(post)
                continue

            self.repo.save_analysis(
                post,
                rewritten=result["rewritten_text"],
                category=result["category"],
                importance=result["importance"],
            )

            history.append(result["rewritten_text"])
            logger.info(f"  └ Принято | Категория: {result['category']}, Важность: {result['importance']}")

    async def _publish_scheduled(self):
        now = datetime.now()

        # Ограничения по времени и интервалам отключены для тестирования
        logger.info("Публикация без ограничений (тестовый режим)")

        ready = self.repo.get_ready_posts()
        if not ready:
            logger.info("Нет постов для публикации")
            return

        match_posts = [p for p in ready if p.category == "match_announce"]
        if not match_posts:
            logger.info("Нет анонсов матчей для публикации")
            return

        for post in match_posts:
            publish_text = (post.rewritten_text or post.text or "").strip()
            if not publish_text:
                logger.info(f"Пост {post.id} — пустой текст, пропускаем")
                self.repo.mark_published(post)
                continue

            await self.publisher.publish(publish_text)
            self.repo.mark_published(post)
            self._last_publish = now
            logger.info(f"Опубликован пост {post.id} (важность {post.importance})")
