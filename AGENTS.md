# AGENTS.md — Внутренняя документация проекта

> Техническая документация для разработки. Для пользовательской документации см. README.md

## Оглавление

- [Архитектура](#архитектура)
- [Пайплайн обработки](#пайплайн-обработки)
- [AI-промпты](#ai-промпты)
- [Конфигурация](#конфигурация)
- [База данных](#база-данных)
- [Тестирование](#тестирование)


---

## Архитектура

### Компоненты системы

```
main.py
  ↓
Pipeline (app/services/pipeline.py)
  ├─→ TelegramParser (app/parsers/telegram_parser.py)
  ├─→ VKParser (app/parsers/vk_parser.py)
  ├─→ AIClient (app/ai/client.py)
  ├─→ Repository (app/database/repository.py)
  └─→ TelegramPublisher (app/publisher/telegram_publisher.py)
```

### Поток данных

```
1. Парсинг
   ├─ Telegram (Telethon) → user_session.session
   └─ VK (vk_api) → service token

2. Сохранение в БД
   Post(source, external_id, text, processed=False)

3. AI-анализ (параллельно, Semaphore(3))
   ├─ Keywords filter (Python) — быстрый pre-filter
   ├─ Accept? (LLM) — организатор или участник?
   ├─ Rewrite (LLM) — форматирование
   └─ Duplicate? (LLM) — сравнение с историей

4. Обновление БД
   Post(rewritten_text, category, importance, processed=True)

5. Публикация
   TelegramPublisher → bot_session.session → @target_channel
```

---

## Пайплайн обработки

### Pipeline.run()

```python
async def run(self):
    if RESET_DB:
        self.repo.reset_db()  # Очистка БД (dev mode)
    else:
        self.repo.reset_analysis()  # Сброс только processed=False
    
    await self._cycle()
```

### Pipeline._cycle()

```python
async def _cycle(self):
    await self._parse_all()      # Парсинг всех источников
    await self._process_posts()  # AI-анализ новых постов
    await self._publish_scheduled()  # Публикация по расписанию
```

### Парсинг источников

**Telegram** (лимит 500 постов):
```python
await self.parser.parse_channel(channel, limit=500)
```

**VK** (лимит 200 постов):
```python
await self.vk_parser.parse_groups(limit=200)
```

### AI-анализ

Конкурентность через `asyncio.Semaphore(3)`:

```python
sem = asyncio.Semaphore(3)
async def process(post):
    async with sem:
        return post, await self.ai.analyze(post.text, history)

results = await asyncio.gather(*[process(p) for p in posts])
```

### Публикация

Условия публикации:
- `PUBLISH_START_HOUR <= current_hour < PUBLISH_END_HOUR`
- Прошло `>= PUBLISH_INTERVAL_MINUTES` с последней публикации
- Есть посты с `category == "match_announce"` и `published == False`

---

## AI-промпты

### 1. Keywords Filter (Python)

**Файл:** `app/ai/client.py:has_basketball_keywords()`

Быстрый pre-filter перед LLM:

```python
BASKETBALL_KEYWORDS = [
    "баскет", "basket", "турнир", "tournament",
    "3х3", "3x3", "стритбол", "streetball",
    ...
]
```

Если ни одного ключевого слова нет → пропуск без LLM-запроса.

### 2. ACCEPT_PROMPT

**Цель:** Отсеять посты, где автор не организует турнир.

**Выход:** `YES` или `NO` (10 токенов max)

**Логика:**
- `YES` — автор **сам организует** турнир, открывает регистрацию, собирает заявки
- `NO` — автор едет на чужой турнир / играет матч / публикует результаты

**Железные правила NO:**
- "едем в / выезжаем в / отправляемся на + город" → `NO`
- "результаты матча" → `NO`
- "собираем команду на турнир [чужой]" → `NO`

**Промпт:**
```
Определи: автор ОРГАНИЗУЕТ турнир (сам проводит, открывает регистрацию) 
или УЧАСТВУЕТ (едет в другой город, играет в чужом турнире)?

ОРГАНИЗУЕТ → YES
УЧАСТВУЕТ → NO

Если есть малейшее сомнение → NO.

[POST]
{text}
[/POST]

Ответ (YES/NO):
```

### 3. REWRITE_PROMPT

**Цель:** Форматировать анонс в единый стиль (few-shot).

**Выход:** 120 токенов max

**Формат эталона:**
```
🏀 Заголовок турнира

📅 дата | ⏰ время | 📍 место

📝 Заявки: контакт

📆 До дедлайна
```

**Правила:**
- Максимум 4 строки (без учёта эмодзи-строк)
- Списки >3 пунктов → удалить целиком
- Формат даты: `12 августа` (без года)
- Разделитель: ` | ` (пробелы вокруг)

**Эталонный пример (пост 2405):**
```
🏀 Благотворительный турнир 3х3 от Grizzly

📅 12 июля | ⏰ 12:00 | 📍 Московский пр., 202

📝 Заявки: @Vladislav_Sharapa

📆 До 10 июля 23:59
```

**Промпт:**
```
Перепиши анонс турнира в короткий формат (max 4 строки):

[ЭТАЛОН]
{эталонный пост 2405}
[/ЭТАЛОН]

[POST]
{text}
[/POST]

Переписанный анонс:
```

### 4. DUPLICATE_PROMPT

**Цель:** Сравнить с последними 20 опубликованными постами.

**Выход:** `YES` (дубликат) или `NO` (уникальный)

**История:** последние 20 `rewritten_text` из БД

**Промпт:**
```
Это дубликат одного из постов в истории?

[ИСТОРИЯ]
{history[-20:]}
[/ИСТОРИЯ]

[НОВЫЙ ПОСТ]
{rewritten_text}
[/НОВЫЙ ПОСТ]

Дубликат? (YES/NO):
```

---

## Конфигурация

### .env

```env
# Telegram API (https://my.telegram.org)
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ

# Источники для парсинга
CHANNEL_IDS=@channel1,@channel2,@channel3
MY_CHANNEL_ID=@output_channel

# VK API (https://dev.vk.ru)
VK_APP_ID=12345678
VK_TOKEN=service_token_from_vk_app_settings
VK_GROUP_IDS=groupname1,groupname2

# Публикация
PUBLISH_START_HOUR=9    # с 9:00
PUBLISH_END_HOUR=21     # до 21:00
PUBLISH_INTERVAL_MINUTES=60  # раз в час

# Dev mode
RESET_DB=True  # False для продакшена
```

### app/config.py

Читает `.env` и преобразует в переменные:

```python
CHANNEL_IDS = os.getenv("CHANNEL_IDS", "").split(",")
VK_GROUP_IDS = os.getenv("VK_GROUP_IDS", "").split(",")
PUBLISH_START_HOUR = int(os.getenv("PUBLISH_START_HOUR", "9"))
RESET_DB = os.getenv("RESET_DB", "False").lower() == "true"
```

---

## База данных

### Модель Post (app/database/models.py)

```python
class Post(Base):
    __tablename__ = "posts"
    
    id: int (PK)
    source: str               # "telegram" | "vk"
    external_id: str          # message.id | "owner_id_post_id"
    text: str                 # Оригинальный текст
    rewritten_text: str       # После AI rewrite
    category: str             # "match_announce" | "other"
    importance: int           # 1-10 (не используется пока)
    processed: bool           # False → AI ещё не обработал
    published: bool           # False → ещё не опубликован
    created_at: datetime
```

### Repository (app/database/repository.py)

**Основные методы:**

```python
def add_post(source, external_id, text):
    # Дедупликация по (source, external_id)
    # processed=False, published=False

def get_unprocessed_posts(limit=50):
    # WHERE processed=False ORDER BY created_at LIMIT {limit}

def save_analysis(post, rewritten, category, importance):
    # UPDATE: rewritten_text, category, importance, processed=True

def mark_skipped(post):
    # UPDATE: category="other", processed=True

def mark_duplicate(post):
    # UPDATE: processed=True

def get_ready_posts():
    # WHERE processed=True AND published=False AND category != "other"

def mark_published(post):
    # UPDATE: published=True

def get_all_rewritten_texts():
    # SELECT rewritten_text WHERE processed=True AND rewritten_text IS NOT NULL
    # ORDER BY created_at DESC
    # Для duplicate check

def reset_db():
    # DROP ALL + CREATE ALL (dev mode)

def reset_analysis():
    # UPDATE posts SET processed=False WHERE published=False
```

---

## Тестирование

### Telegram посты (result.json)

**Источник:** Экспорт 2313 сообщений из @grizzlylivespb

**Тесты (19 постов):**
- ✅ **9 GOOD → ACCEPT** (организует турнир)
- ✅ **10 BAD → REJECT** (участвует / результаты)

**Эталоны:**

| ID | Тип | Описание |
|----|-----|----------|
| 2405 | GOOD | Эталон для REWRITE_PROMPT |
| 498, 522, 530, 531 | GOOD | Благотворительные турниры 3х3 |
| 1262, 1484, 1542, 2156 | GOOD | Кубки Grizzly, Girls Battle |
| 2388, 2394, 698, 1419, 1841 | BAD | "едем в Петрозаводск/Мончегорск" |
| 2408 | BAD | Анонс матча команды |
| 2478 | BAD | Собирает команду на чужой турнир |
| 2476 | BAD | Пост-релиз прошедшего турнира |
| 2358 | BAD | "Клубный турнир" (тренировка) |

### VK посты (bkgrizzlyspb)

**Утилиты:**
- `tmp/fetch_vk_posts.py` — парсит N последних постов из VK группы
- `tmp/vk_test.py` — прогоняет через AI-пайплайн

**Запуск:**
```bash
# 1. Получить реальные посты
python tmp/fetch_vk_posts.py
# → tmp/vk_posts_stub.json

# 2. Протестировать AI
python tmp/vk_test.py
# → tmp/vk_summary.json
```

**Результаты (01.08.2026, 20 постов):**
- ✅ **2 ACCEPT** (3685 — набор в команду, 3646 — благотворительный турнир)
- ✅ **18 REJECT** (результаты, выезды, новости команды)

**Эталонный пост:** [3635](https://vk.ru/wall-214726107_3635) — "организует турнир" (закреплённый)

### Производительность

**Железо:** Apple M2, Metal GPU  
**Модель:** qwen2.5:7b (Q4_K_M, 7.6B параметров)  
**Время на пост:** 15-25 сек (3 LLM-запроса)

**Breakdown:**
- ACCEPT_PROMPT: ~3-5 сек (10 токенов)
- REWRITE_PROMPT: ~10-15 сек (120 токенов)
- DUPLICATE_PROMPT: ~3-5 сек (10 токенов)

**Конкурентность:** `Semaphore(3)` — до 3 постов параллельно

## Roadmap

### TODO
- [ ] Добавить фильтр даты в ACCEPT_PROMPT ("турнир в прошлом" → NO)
- [ ] Логирование AI-решений (почему ACCEPT/REJECT)
- [ ] Мониторинг ошибок VK API (rate limits, invalid token)
- [ ] Web-интерфейс для ручного одобрения постов (модерация)
- [ ] Поддержка Instagram парсинга (если появится API)
- [ ] Telegram-бот для управления (старт/стоп, статистика)

### Потенциальные улучшения
- Переход на streaming LLM API (быстрее для rewrite)
- Кеширование AI-результатов (если пост повторяется)
- A/B тесты промптов (сравнение точности)
- Fine-tuning модели на баскетбольных анонсах
- Поддержка multi-языковых постов (English, Русский)

---

## Контакты

**Разработчик:** [smetanamzh](https://github.com/smetanamzh)  
**Репозиторий:** https://github.com/smetanamzh/avi

---

*Последнее обновление: 2026-08-01*
