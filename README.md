# Basket — AI-агрегатор баскетбольных турниров

Автоматический парсер и агрегатор анонсов баскетбольных турниров из Telegram и VK. Использует локальную LLM (Ollama) для фильтрации и форматирования постов.

## Возможности

- 🔍 **Парсинг** Telegram-каналов и VK-групп
- 🤖 **AI-фильтрация** — отсеивает посты о выездах, результатах матчей, оставляя только анонсы турниров
- ✍️ **Автоматический рерайт** — форматирует посты в единый стиль
- 🔄 **Обнаружение дубликатов** — сравнивает с историей последних 20 постов
- 📤 **Публикация** в Telegram-канал

## Архитектура

```
┌─────────────┐
│  Telegram   │──┐
│  VK Groups  │  │
└─────────────┘  │
                 ↓
        ┌────────────────┐
        │    Pipeline    │
        └────────────────┘
                 ↓
        ┌────────────────┐
        │  AI Analysis   │
        │  (3 запроса)   │
        └────────────────┘
                 ↓
        ┌────────────────┐
        │   SQLite DB    │
        └────────────────┘
                 ↓
        ┌────────────────┐
        │ Telegram Bot   │
        └────────────────┘
```

### Пайплайн обработки

```
Post → Keywords filter → Accept? → Rewrite → Duplicate check → Publish
       (Python)          (LLM)     (LLM)     (LLM)
```

**3 LLM-запроса на пост:**
1. **Accept** (10 токенов) — организатор или участник?
2. **Rewrite** (120 токенов) — форматирование в единый стиль
3. **Duplicate** (10 токенов) — проверка на повтор

**Производительность:** ~15-25 сек на пост (qwen2.5:7b на M2)

## Установка

### Требования

- Python 3.12+
- [Ollama](https://ollama.ai/) с моделью `qwen2.5:7b`
- Telegram API credentials (API_ID, API_HASH)
- Telegram Bot Token
- VK App ID и Service Token

### Установка зависимостей

```bash
# Клонируйте репозиторий
git clone https://github.com/smetanamzh/avi.git
cd avi

# Создайте виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или .venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt
# или с uv:
uv pip install -e .
```

### Настройка

Создайте файл `.env` в корне проекта:

```env
# Telegram API (получить на https://my.telegram.org)
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token

# Каналы для парсинга (через запятую)
CHANNEL_IDS=@channel1,@channel2
MY_CHANNEL_ID=@your_output_channel

# VK API (получить на https://dev.vk.ru)
VK_APP_ID=your_app_id
VK_TOKEN=your_service_token
VK_GROUP_IDS=groupname1,groupname2
```

### Инициализация БД

```bash
python scripts/init_db.py
```

## Использование

### Запуск парсинга

```bash
python main.py
```

### Автономный режим (цикличный запуск)

```bash
python main.py --loop
```

Цикл по умолчанию: каждые 6 минут.

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
│   └── config.py              # Конфигурация из .env
├── scripts/
│   └── init_db.py             # Инициализация БД
├── tmp/
│   ├── fetch_vk_posts.py      # Утилита для теста VK API
│   └── vk_test.py             # Тест AI-пайплайна на VK постах
└── main.py                     # Точка входа
```

## AI-промпты

### Accept Prompt

Отсеивает посты, где автор:
- Едет на чужой турнир (`"едем в Петрозаводск"` → REJECT)
- Публикует результаты матча → REJECT
- Собирает команду для участия → REJECT

Принимает посты, где автор:
- **Сам организует** турнир
- Открывает регистрацию
- Собирает заявки

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

## Тестирование

### Telegram посты

Проект протестирован на 2313 сообщениях из реального канала:
- **19/19 правильных классификаций**
- 9 GOOD → ACCEPT
- 10 BAD → REJECT

### VK посты

```bash
# Получить реальные посты из VK
python tmp/fetch_vk_posts.py

# Прогнать через AI-пайплайн
python tmp/vk_test.py
```

Результаты (20 постов из `bkgrizzlyspb`):
- **2 ACCEPT, 18 REJECT**
- Корректная работа с service token

## Технологии

- **Python 3.12** — основной язык
- **Ollama + qwen2.5:7b** — локальная LLM для анализа
- **Telethon** — парсинг Telegram
- **vk_api** — парсинг VK
- **SQLAlchemy** — ORM для SQLite
- **asyncio** — конкурентная обработка (Semaphore 3)

## Производительность

- **Модель:** qwen2.5:7b (Q4_K_M, 7.6B параметров)
- **Железо:** Apple M2 Metal GPU
- **Скорость:** 15-25 сек на пост (3 LLM-запроса)
- **Конкурентность:** до 3 постов параллельно

## Лицензия

MIT

## Автор

[smetanamzh](https://github.com/smetanamzh)

---

**Примечание:** Проект создан для агрегации анонсов баскетбольных турниров. Все API credentials должны быть получены легально через официальные каналы (Telegram, VK).
