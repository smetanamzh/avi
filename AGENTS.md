# Basket — AI-агрегатор баскетбольных турниров

## Описание проекта
Парсит Telegram-каналы, ищет среди постов анонсы открытых баскетбольных турниров через локальную LLM (Ollama), и публикует отобранные в свой канал.

## Архитектура
- `main.py` — точка входа: инициализация БД → Pipeline
- `app/services/pipeline.py` — оркестратор: парсинг → AI-анализ → публикация
- `app/parsers/telegram_parser.py` — парсинг Telegram-каналов (user_session)
- `app/parsers/vk_parser.py` — парсинг VK-групп через VK API (service token)
- `app/ai/client.py` — 3 отдельных LLM-запроса (accept → rewrite → duplicate)
- `app/publisher/telegram_publisher.py` — публикация в канал (бот)
- `app/database/repository.py` — CRUD для SQLite
- `app/database/models.py` — модель Post (source, external_id, text, rewritten_text, category, importance, processed, published)
- `app/config.py` — конфиги из .env

## Пайплайн обработки поста
```
Post
  ↓
Keywords (Python) — быстрый pre-filter
  ↓
Accept? (LLM, 10 токенов) — автор сам организует турнир?
  ↓
Rewrite (LLM, 120 токенов) — короткий анонс в формате эталона
  ↓
Duplicate (LLM, 10 токенов) — сверка с последними 20 постами
  ↓
Publish
```
Всего **3 вызова LLM** на пост. Конкурентность: Semaphore(3).

## Промпты (app/ai/client.py)

### ACCEPT_PROMPT
- YES: автор сам проводит турнир, открывает регистрацию, собирает заявки
- NO: автор едет/участвует в чужом турнире, играет матч, публикует результаты
- Ключевой признак NO: "едем в / выезжаем в / отправляемся на + город"
- "Если есть хоть малейшее сомнение — NO"

### REWRITE_PROMPT
Few-shot с эталоном. Формат вывода:
```
🏀 Заголовок

📅 дата | ⏰ время | 📍 место

📝 Заявки: контакт

📆 До дедлайна
```
Максимум 4 строки. Списки длиннее 3 пунктов — удалять целиком.

### DUPLICATE_PROMPT
Сравнение с историей из 20 последних rewritten_texts.

## Модель
- `qwen2.5:7b` (Q4_K_M, 7.6B)
- Apple M2 Metal GPU
- ~15-25 сек на пост (3 запроса: 2×10 токенов + 1×120 токенов)

## Текущее состояние (20.07.2026)
- Парсинг: Telegram через Telethon (user_session) + VK через VK API (token)
- AI-анализ: 3 простых промпта (NO JSON), `num_predict=120` для rewrite
- Публикация: только `match_announce`, 24/7, без фильтра по часам
- `RESET_DB = True` — БД чистится при каждом запуске
- Тесты на result.json: **19/19 правильных** (9 GOOD → ACCEPT, 10 BAD → REJECT)

## Что было сделано

### 20.07 — Полный рефакторинг AI-клиента
- Убран JSON из ответа модели — 3 отдельных простых промпта
- ACCEPT_PROMPT объединил classify + organizer (минус 1 вызов)
- REWRITE_PROMPT: few-shot с эталоном (пост 2405), формат через `|`, макс 4 строки
- `num_predict` для rewrite: 256 → 120 (нечем разгоняться)
- Duplicate: history[-3:] → history[-20:] (ловим повторы)
- `prompts.py` удалён (промпты inline)
- Все промпты generic — нет упоминаний Grizzly
- Добавлено железное правило reject: "едет/выезжает в другой город = PARTICIPANT"
- Тесты 19/19: 9 GOOD → ACCEPT, 10 BAD → REJECT
- Результаты тестов сохранены в `tmp/`

### Ранее
- Создан AGENTS.md, файловое логирование, конкурентные AI-запросы (Semaphore 3)
- Pre-filter по ключевым словам баскетбола
- Публикация всех принятых `match_announce`, не только первого
- Сброс старых анализов при старте (reset_analysis)

### 31.07 — VK парсинг
- Добавлена библиотека `vk_api` в зависимости
- `app/parsers/vk_parser.py` — парсинг стен VK-групп через API метод `wall.get`
- VK парсер интегрирован в Pipeline (`_parse_all`), работает параллельно с Telegram
- Конфиг: `VK_APP_ID=54702541`, `VK_TOKEN` (service token из настроек VK-приложения), `VK_GROUP_IDS=bkgrizzlyspb` в `.env`
- VK посты сохраняются с `source="vk"`, `external_id` = `owner_id_post_id`
- Поддержка пагинации: до 100 постов за запрос, `offset`-based, лимит 200 по умолчанию
- Поддержка разных форматов ID группы: short name (`bkgrizzlyspb`), `club123456`, `-123456`, `123456`
- Удалён `scripts/vk_auth.py` — service token не требует авторизации через логин/пароль

### 01.08 — Очистка проекта и тестирование VK
- Удалены все временные файлы из `tmp/`: `*_GOOD.json`, `*_BAD*.json`, `vk_test_*.json`, `client_*.py`, `*_summary.json`
- Оставлены только утилиты: `tmp/fetch_vk_posts.py`, `tmp/vk_test.py`, `tmp/vk_posts_stub.json`
- Протестирован реальный парсинг группы `bkgrizzlyspb` с рабочим service token
- Структура проекта симметрична: Telegram (parser + publisher), VK (parser)

## result.json
Экспорт чата с Telegram (@grizzlylivespb). 2313 сообщений.

**GOOD (организует, принимать):**
- 498 — благотворительный турнир 3х3, Grizzly проводит
- 522 — благотворительный турнир 3х3, Grizzly проводит
- 530 — "МЫ ОРГАНИЗУЕМ" женский турнир 1х1
- 531 — Grizzly организовывает первый женский турнир 1х1
- 1262 — Кубок Grizzly 3x3, приглашают команды
- 1484 — Girls Battle 1x1, Grizzly организовывает
- 1542 — благотворительный турнир 3х3
- 2156 — Кубок Grizzly 3х3, женский
- 2405 — **эталон**: Grizzly организует благотворительный турнир, заявки @Vladislav_Sharapa

**BAD (участвует, отклонять):**
- 2388/2394 — Кубок Дружбы, "едет в Петрозаводск"
- 698/2102/1419 — "выезжаем/едем в Петрозаводск"
- 2408 — анонс матча команды Grizzly vs Валькирия
- 2478 — собирает команду на чужой турнир "Аквамарин"
- 2476 — пост-релиз прошедшего турнира
- 2358 — "последняя тренировка, устроили клубный турнир"
- 1841 — "едем в Мончегорск"

## Тестирование VK постов

### tmp/fetch_vk_posts.py
Получает реальные посты из VK группы и сохраняет в `tmp/vk_posts_stub.json`.

**Запуск:**
```bash
.venv/bin/python tmp/fetch_vk_posts.py
```

### tmp/vk_test.py
Быстрый тест AI-пайплайна (accept → rewrite → duplicate) на VK постах.

**Запуск:**
```bash
.venv/bin/python tmp/vk_test.py
```

**Источник постов:**
1. Если существует `tmp/vk_posts_stub.json` — читается оттуда (формат VK API `wall.get` response).
2. Иначе используются 4 stub-поста (2 GOOD, 2 BAD) из `_default_stub()` в скрипте.

### Результаты тестов (01.08.2026)
- Протестировано 20 реальных постов из `bkgrizzlyspb`
- **2 ACCEPT, 18 REJECT**
- Service token работает корректно (`e8b030c9...`)
- Эталонный пост 3635 ("организует турнир") присутствует в `vk_posts_stub.json` (закреплённый)

## Важные замечания
- Канал-источник: @grizzlylivespb
- Канал-приёмник: @govnomp2170
- Модель: qwen2.5:7b
- База: SQLite (basketball.db), чистится при каждом запуске (RESET_DB=True)
- Сессии: user_session.session (Telegram парсинг), bot_session.session (Telegram публикация)
- VK токен: service token из настроек VK-приложения → `VK_TOKEN` в `.env`
- VK группы: `VK_GROUP_IDS` в `.env` (short name, clubID, или -ID)
- Предложка: @govnobasket
