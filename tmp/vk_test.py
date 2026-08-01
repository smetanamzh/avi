"""
Quick test of AI pipeline (accept → rewrite → duplicate) on VK wall posts.

Usage:
    .venv/bin/python tmp/vk_test.py

By default it uses stub VK posts (tmp/vk_posts_stub.json).
To test against real VK wall, replace that file with output of:
    from app.parsers.vk_parser import VKParser
    p = VKParser()
    owner = p._resolve_group_id("bkgrizzlyspb")
    posts = p._fetch_wall(owner, 30)
    json.dump(posts, open("tmp/vk_posts_stub.json","w"), ensure_ascii=False, indent=2)
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# project root in sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.ai.client import AIClient, has_basketball_keywords

TMP_DIR = Path(__file__).parent
STUB_FILE = TMP_DIR / "vk_posts_stub.json"


def load_vk_texts() -> list[dict]:
    """Return list of {id, text} from stub file or empty."""
    if not STUB_FILE.exists():
        print(f"  {STUB_FILE.name} — не найден, использую stub-данные")
        return _default_stub()

    with open(STUB_FILE, encoding="utf-8") as f:
        posts = json.load(f)

    texts = []
    for post in posts:
        text = post.get("text", "")
        if not text:
            continue
        texts.append({"id": post.get("id"), "text": text})
    return texts


def _default_stub() -> list[dict]:
    """
    Stub VK posts — замените tmp/vk_posts_stub.json реальными постами.
    Сейчас 4 примера: 2 GOOD (организует) + 2 BAD (участвует / результаты).
    """
    return [
        {
            "id": "vk1_GOOD",
            "text": "🏀 Благотворительный турнир 3х3 от Grizzly! 15 августа, 13:00, Московский проспект 202. Заявки @Vladislav_Sharapa до 13 августа. Взнос — корм для приюта 🐾",
        },
        {
            "id": "vk2_GOOD",
            "text": "💥 Женский турнир 1х1 — приглашаем девушек! 20 июня, 14:00, Баскетбольная площадка Ленина, 5. Регистрация @TournamentLadyboss",
        },
        {
            "id": "vk3_BAD",
            "text": "Кубок Дружбы 2024. Мы едем в Петрозаводск 10–12 августа. Ждём всех в Тулассе, встречаемся в аэропорту в 9:00. #grizzly #basket",
        },
        {
            "id": "vk4_BAD",
            "text": "Матч Grizzly vs Валькирия прошёл сегодня! Счёт 78:65. Фото результатов ниже 👇 Благодарим всех участников и болельщиков!",
        },
    ]


async def run_tests(posts: list[dict], limit: int = 50):
    ai = AIClient()
    results = []
    history = []  # rewritten_texts of ACCEPTED posts

    for i, post in enumerate(posts[:limit]):
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

        per_file = TMP_DIR / f"vk_test_{pid}.json"
        with open(per_file, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)

    summary_file = TMP_DIR / "vk_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    accepted = sum(1 for r in results if r["verdict"] == "ACCEPT")
    rejected = sum(1 for r in results if r["verdict"] == "REJECT")
    print(f"\nDone: {accepted} ACCEPTED, {rejected} REJECTED, {len(results)} total")
    print(f"Summary → {summary_file.relative_to(Path.cwd())}")
    return results


async def main():
    posts = load_vk_texts()
    if not posts:
        print("Нет постов для теста.")
        return
    print(f"Тест постов: {len(posts)}")
    await run_tests(posts, limit=20)


if __name__ == "__main__":
    asyncio.run(main())
