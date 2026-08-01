"""
Fetch real VK posts from bkgrizzlyspb and save to tmp/vk_posts_stub.json
Usage: .venv/bin/python tmp/fetch_vk_posts.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.parsers.vk_parser import VKParser

def main():
    parser = VKParser()

    print("Получаем ID группы bkgrizzlyspb...")
    owner_id = parser._resolve_group_id("bkgrizzlyspb")
    if owner_id is None:
        print("❌ Не удалось получить ID группы")
        return

    print(f"✅ owner_id = {owner_id}")
    print("Парсим последние 30 постов...")

    posts = parser._fetch_wall(owner_id, limit=30)

    if not posts:
        print("❌ Постов не найдено (проверь VK_TOKEN в .env)")
        return

    stub_file = Path(__file__).parent / "vk_posts_stub.json"
    with open(stub_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"✅ Сохранено {len(posts)} постов → {stub_file.name}")
    print("\nТеперь запусти: .venv/bin/python tmp/vk_test.py")

if __name__ == "__main__":
    main()
