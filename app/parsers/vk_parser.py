import asyncio
import logging

from app.config import VK_GROUP_IDS, VK_TOKEN
from app.database.repository import Repository

logger = logging.getLogger("basket")


class VKParser:

    def __init__(self):
        self.token = VK_TOKEN
        self.repo = Repository()

    def _get_client(self):
        import vk_api

        return vk_api.VkApi(token=self.token)

    def _resolve_group_id(self, group: str) -> int:
        """Convert a group identifier (short name or club ID) to numeric owner_id."""
        group = group.strip()

        if group.startswith("club") or group.startswith("public"):
            return -int("".join(ch for ch in group if ch.isdigit()))

        if group.startswith("-") and group[1:].isdigit():
            return int(group)

        if group.isdigit():
            return -int(group)

        if group.startswith("@"):
            group = group[1:]

        client = self._get_client()
        result = client.method("groups.getById", {"group_id": group})
        if not result:
            logger.warning(f"Не удалось разрешить группу {group}")
            return None

        return -int(result[0]["id"])

    def _fetch_wall(self, owner_id: int, limit: int = 100) -> list[dict]:
        """Fetch wall posts from a VK group using offset-based pagination."""
        client = self._get_client()
        posts = []
        offset = 0

        while len(posts) < limit:
            chunk = min(100, limit - len(posts))
            response = client.method(
                "wall.get",
                {"owner_id": owner_id, "count": chunk, "offset": offset},
            )

            if not response or "items" not in response:
                break

            items = response["items"]
            if not items:
                break

            posts.extend(items)
            offset += len(items)

            if len(items) < chunk:
                break

        return posts

    async def parse_groups(self, groups: list[str] | None = None, limit: int = 200):
        groups = groups or VK_GROUP_IDS
        if not groups:
            logger.info("VK_GROUP_IDS не заданы, пропускаем VK")
            return

        if not self.token:
            logger.warning("VK_TOKEN не задан, пропускаем VK")
            return

        logger.info("Подключились к VK API")

        for group in groups:
            owner_id = await asyncio.to_thread(self._resolve_group_id, group)
            if owner_id is None:
                continue

            logger.info(f"Парсим VK группа: {group} (owner_id={owner_id})")

            wall_posts = await asyncio.to_thread(self._fetch_wall, owner_id, limit)
            if not wall_posts:
                logger.info(f"  └ Нет постов в {group}")
                continue

            count = 0
            for post in wall_posts:
                text = post.get("text", "")
                if not text:
                    continue

                post_id = post.get("id")
                if not post_id:
                    continue

                count += 1
                self.repo.add_post(
                    source="vk",
                    external_id=f"{owner_id}_{post_id}",
                    text=text,
                )

            logger.info(f"  └ Сохранили в БД: {count} постов")

        logger.info("VK парсинг завершён")
