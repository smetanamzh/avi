import asyncio
import sys

from app.database.database import init_db
from app.logger import setup_logger
from app.services.pipeline import Pipeline

logger = setup_logger()


async def main():
    logger.info("=== Запуск Basket ===")
    init_db()

    pipeline = Pipeline()

    if "--once" in sys.argv:
        logger.info("Режим: однократный запуск")
        await pipeline.run()
    else:
        logger.info("Режим: автономный (каждые 15 мин)")
        await pipeline.run_forever(cycle_minutes=15)

    logger.info("=== Завершено ===")


if __name__ == "__main__":
    asyncio.run(main())
