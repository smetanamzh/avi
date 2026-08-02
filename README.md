# Basket

AI-агрегатор баскетбольных турниров из Telegram и VK с автоматической фильтрацией и публикацией.

## Что делает

Парсит посты из Telegram-каналов и VK-групп, фильтрует через локальную LLM (Ollama) и автоматически публикует анонсы турниров в целевой канал.

**Пайплайн:**
```
Telegram/VK → Keywords filter → AI accept → AI rewrite → Duplicate check → Publish
```

**3 LLM-запроса на пост:**
1. Accept (10 токенов) — организатор или участник?
2. Rewrite (120 токенов) — форматирование в единый стиль
3. Duplicate (10 токенов) — проверка на повтор с последними 20 постами

**Производительность:** 15-25 сек/пост (qwen2.5:7b на M2)

## Установка

### Требования

- Python 3.12+
- [Ollama](https://ollama.ai/) с моделью `qwen2.5:7b`
- Telegram API credentials ([my.telegram.org](https://my.telegram.org))
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- VK App ID и Service Token ([vk.dev](https://dev.vk.ru))

### Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/smetanamzh/basket.git
cd basket

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или .venv\Scripts\activate на Windows

# Установить зависимости
pip install -r requirements.txt
# или с uv:
uv pip install -e .

# Создать .env
cp .env.example .env
# Заполнить API credentials в .env

# Инициализировать БД
python scripts/init_db.py

# Запустить
python main.py --once  # однократный запуск
python main.py         # автономный режим (каждые 15 мин)
```

## Конфигурация

Создайте `.env` в корне проекта:

```env
# Telegram API (получить на https://my.telegram.org)
API_ID=12345678
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token

# Каналы для парсинга (через запятую)
CHANNEL_IDS=@channel1,@channel2
MY_CHANNEL_ID=@your_output_channel

# VK API (получить на https://dev.vk.ru)
VK_APP_ID=12345678
VK_TOKEN=your_service_token
VK_GROUP_IDS=groupname1,groupname2

# Расписание публикации
PUBLISH_START_HOUR=9           # с 9:00
PUBLISH_END_HOUR=21            # до 21:00
PUBLISH_INTERVAL_MINUTES=60    # раз в час

# Dev mode (False для production!)
RESET_DB=False
```

## Структура проекта

```
basket/
├── app/
│   ├── ai/
│   │   └── client.py          # AI-клиент (3 промпта)
│   ├── database/
│   │   ├── models.py          # SQLAlchemy модели
│   │   └── repository.py      # CRUD операции
│   ├── parsers/
│   │   ├── telegram_parser.py # Парсинг Telegram
│   │   └── vk_parser.py       # Парсинг VK
│   ├── publisher/
│   │   └── telegram_publisher.py # Публикация в Telegram
│   ├── services/
│   │   └── pipeline.py        # Оркестратор
│   ├── config.py              # Конфигурация из .env
│   └── logger.py              # Настройка логирования
├── scripts/
│   └── init_db.py             # Инициализация БД
└── main.py                    # Точка входа
```

## Как работает AI

### Accept Prompt

Отсеивает посты, где автор:
- ❌ Едет на чужой турнир ("едем в Петрозаводск")
- ❌ Публикует результаты матча
- ❌ Собирает команду для участия

Принимает посты, где автор:
- ✅ Сам организует турнир
- ✅ Открывает регистрацию
- ✅ Собирает заявки

### Rewrite Prompt

Few-shot форматирование в единый стиль:

```
🏀 Заголовок

📅 дата | ⏰ время | 📍 место

📝 Заявки: контакт

📆 До дедлайна
```

Максимум 4 строки, списки >3 пунктов удаляются.

### Duplicate Prompt

Сравнивает с последними 20 опубликованными постами.

## Производительность

- **Модель:** qwen2.5:7b (Q4_K_M, 7.6B параметров)
- **Железо:** Apple M2 Metal GPU
- **Скорость:** 15-25 сек на пост (3 LLM-запроса)
- **Конкурентность:** до 3 постов параллельно (asyncio.Semaphore)

## Тестирование

Проект протестирован на реальных данных:
- **Telegram:** 19/19 правильных классификаций (2313 сообщений)
- **VK:** 2/20 ACCEPT на реальных постах из `bkgrizzlyspb`

## Технологии

- **Python 3.12** — основной язык
- **Ollama + qwen2.5:7b** — локальная LLM для анализа
- **Telethon** — парсинг Telegram
- **vk_api** — парсинг VK
- **SQLAlchemy** — ORM для SQLite
- **asyncio** — конкурентная обработка

## Разработка

Техническая документация для разработчиков — см. [AGENTS.md](AGENTS.md)

Список задач — см. [TODO.md](TODO.md)

## Лицензия

MIT

## Автор

[smetanamzh](https://github.com/smetanamzh)

---

**Примечание:** Проект создан для агрегации анонсов баскетбольных турниров. Все API credentials должны быть получены легально через официальные каналы.
