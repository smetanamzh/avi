"""
Quick test of AI pipeline (accept → rewrite → duplicate) on VK wall posts.

Usage:
    .venv/bin/python tmp/vk_test.py

Fetches posts directly from VK API and tests AI analysis.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# project root in sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.ai.client import AIClient, has_basketball_keywords
from app.parsers.vk_parser import VKParser

TMP_DIR = Path(__file__).parent


async def fetch_vk_posts(group: str = "bkgrizzlyspb", limit: int = 30) -> list[dict]:
    """Fetch posts directly from VK API."""
    parser = VKParser()

    logging.info(f"Получаем ID группы {group}...")
    owner_id = await asyncio.to_thread(parser._resolve_group_id, group)
    if owner_id is None:
        logging.error(f"Не удалось получить ID группы {group}")
        return []

    logging.info(f"owner_id = {owner_id}")
    logging.info(f"Парсим последние {limit} постов...")

    posts = await asyncio.to_thread(parser._fetch_wall, owner_id, limit)

    if not posts:
        logging.warning("Постов не найдено (проверь VK_TOKEN в .env)")
        return []

    # Convert to simplified format
    result = []
    for post in posts:
        text = post.get("text", "")
        if not text:
            continue
        result.append({"id": post.get("id"), "text": text})

    logging.info(f"Получено {len(result)} постов с текстом")
    return result


async def run_tests(posts: list[dict]):
    """Run AI analysis on posts."""
    ai = AIClient()
    results = []
    history = []  # rewritten_texts of ACCEPTED posts

    for i, post in enumerate(posts):
        pid = post["id"]
        text = post["text"]
        logging.info(f"[{i+1}/{len(posts)}] VK id={pid}")

        kw = has_basketball_keywords(text)
        result = await ai.analyze(text, history)

        entry = {
            "id": pid,
            "keywords": kw,
            "accept": result["accept"],
            "duplicate": result["duplicate"],
            "category": result["category"],
            "rewritten": result["rewritten_text"],
            "verdict": (
                "ACCEPT" if result["accept"] and not result["duplicate"]
                else "REJECT"
            ),
        }
        results.append(entry)

        if result["accept"] and not result["duplicate"]:
            history.append(result["rewritten_text"])

    summary_file = TMP_DIR / "vk_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    accepted = sum(1 for r in results if r["verdict"] == "ACCEPT")
    rejected = sum(1 for r in results if r["verdict"] == "REJECT")

    print(f"\n{'='*60}")
    print(f"Результаты: {accepted} ACCEPTED, {rejected} REJECTED, {len(results)} total")
    print(f"Summary → {summary_file.relative_to(Path.cwd())}")
    print(f"{'='*60}\n")

    # Print accepted posts
    if accepted > 0:
        print("Принятые посты:")
        for r in results:
            if r["verdict"] == "ACCEPT":
                print(f"  • VK id={r['id']}")
                print(f"    {r['rewritten'][:100]}...")
        print()

    return results


async def main():
    # Fetch posts from VK
    posts = await fetch_vk_posts(group="bkgrizzlyspb", limit=30)

    if not posts:
        print("❌ Нет постов для теста.")
        return

    print(f"\n{'='*60}")
    print(f"Тестируем {len(posts)} постов из VK группы bkgrizzlyspb")
    print(f"{'='*60}\n")

    await run_tests(posts)


if __name__ == "__main__":
    asyncio.run(main())
