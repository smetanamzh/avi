# TODO — Список задач

> Актуальные задачи для развития проекта Basket

---

## 🔥 Критичные (блокируют production)

- [ ] **RESET_DB hardcoded в config.py**  
  `app/config.py:25` — `RESET_DB = True` чистит БД при каждом запуске  
  *Fix:* Читать из `.env`:
  ```python
  RESET_DB = os.getenv("RESET_DB", "False").lower() == "true"
  ```

- [ ] **Фильтр даты в ACCEPT_PROMPT**  
  AI принимает посты о прошедших турнирах (пост "12 июля" пройдёт, хотя сегодня 2 августа)  
  *Fix:* `app/ai/client.py:29` — добавить в промпт:
  ```python
  ACCEPT_PROMPT = f"""
  ВАЖНО: Если турнир уже прошёл → NO.
  Сегодня: {datetime.now().strftime('%d %B %Y')}
  
  [остальной промпт...]
  """
  ```

- [ ] **Обработка ошибок VK API**  
  `app/parsers/vk_parser.py:45-71` — падает при invalid token, rate limit, network timeout  
  *Fix:* Обернуть в try/except:
  ```python
  try:
      response = client.method("wall.get", {...})
  except Exception as e:
      logger.error(f"VK API error for {owner_id}: {e}")
      return []
  ```

- [ ] **Несоответствие cycle_minutes**  
  `main.py:22` — `cycle_minutes=15`, но в документации "каждые 6 минут"  
  *Fix:* Вынести в `.env`:
  ```python
  CYCLE_MINUTES = int(os.getenv("CYCLE_MINUTES", "6"))
  ```

---

## ⚙️ Средний приоритет (качество кода)

- [ ] **Дублирование reset_db в Pipeline**  
  `app/services/pipeline.py:35-46` — один и тот же блок в `run()` и `run_forever()`  
  *Fix:* Вынести в метод `_init_db()`

- [ ] **Магические числа в AI client**  
  `app/ai/client.py:147,151,161` — hardcoded `num_predict=10,120,10`  
  *Fix:* Вынести в константы:
  ```python
  ACCEPT_MAX_TOKENS = 10
  REWRITE_MAX_TOKENS = 120
  DUPLICATE_MAX_TOKENS = 10
  ```

- [ ] **Логи без rotation**  
  `pipeline.log` растёт бесконечно  
  *Fix:* В `app/logger.py` добавить `RotatingFileHandler` (макс 10MB, 3 бэкапа)

- [ ] **Индексы в БД**  
  Нет индексов на `(source, external_id)`, `processed`, `published` → медленные запросы  
  *Fix:* В `app/database/models.py`:
  ```python
  __table_args__ = (
      Index('idx_source_external', 'source', 'external_id'),
      Index('idx_processed', 'processed'),
      Index('idx_published', 'published'),
  )
  ```

- [ ] **AI decision logging**  
  Записывать почему пост был ACCEPT/REJECT  
  *Пример:* `Post.ai_decision_log = "REJECT: найдено 'едем в Петрозаvodsk'"`

---

## 💡 Низкий приоритет (Nice to have)

- [ ] **Web-интерфейс для модерации**  
  Ручное одобрение постов перед публикацией (Flask + простая админка)  
  Фичи:
  - Список постов в очереди (`processed=True, published=False`)
  - Кнопки: Approve / Reject / Edit
  - История опубликованных постов

- [ ] **Telegram-бот для управления**  
  Команды:
  - `/start` — запустить парсинг
  - `/stop` — остановить
  - `/stats` — статистика (сколько постов обработано/опубликовано)
  - `/last` — последние 5 опубликованных постов

- [ ] **Monitoring и алерты**  
  Уведомления в Telegram при ошибках:
  - Упал VK API
  - Ollama не отвечает
  - Не удалось опубликовать пост

- [ ] **A/B тесты промптов**  
  Сравнить точность разных версий ACCEPT_PROMPT на тестовом датасете

- [ ] **Fine-tuning модели**  
  Дообучить qwen2.5:7b на баскетбольных анонсах (если накопится >500 примеров)

- [ ] **Кеширование AI-результатов**  
  Если тот же пост парсится повторно → брать из кеша (Redis/SQLite)

- [ ] **Поддержка Instagram**  
  Парсинг через unofficial API (если найдётся стабильное решение)

- [ ] **Multi-языковая поддержка**  
  Английские анонсы турниров (для зарубежных источников)

---

## 🐛 Известные баги

- [ ] **RESET_DB=True в production**  
  Опасно! БД чистится при каждом запуске  
  *Fix:* Переместить в `.env`, по умолчанию `False`

- [ ] **Турниры в прошлом проходят фильтр**  
  ACCEPT_PROMPT не проверяет дату турнира  
  *Fix:* Добавить проверку даты с текущей датой

- [ ] **VK парсер падает при ошибках API**  
  Нет обработки invalid token, rate limit, network errors  
  *Fix:* try/except + логирование

---

## 📋 План на ближайшие шаги

### Шаг 1: Критичные фиксы (30 мин)
1. `RESET_DB` из `.env` (app/config.py)
2. Фильтр даты в ACCEPT_PROMPT (app/ai/client.py)
3. Обработка ошибок VK API (app/parsers/vk_parser.py)
4. `CYCLE_MINUTES` из `.env` (main.py, app/config.py)

### Шаг 2: Тестовый запуск (15 мин)
```bash
# Проверить .env
cat .env  # API_ID, BOT_TOKEN, MY_CHANNEL_ID, RESET_DB=False

# Запустить Pipeline однократно
python main.py --once

# Проверить логи
tail -f pipeline.log

# Проверить канал — появились ли новые посты?
```

### Шаг 3: Code quality (1 час)
1. Рефакторинг Pipeline._init_db()
2. Константы для AI tokens
3. RotatingFileHandler для логов
4. Индексы в БД

### Шаг 4: Production deploy
1. `.env` → `RESET_DB=False`
2. Запустить в автономном режиме: `python main.py`
3. Мониторинг логов первые 2-3 цикла

---

## ✅ Завершённые задачи

- [x] **README.md для GitHub** *(2026-08-01)*  
  Публичная документация проекта

- [x] **Переписать AGENTS.md** *(2026-08-01)*  
  Техническая документация для разработчиков

- [x] **Удалить .opencode из git** *(2026-08-01)*  
  Не нужна в репозитории

- [x] **Очистить tmp/ от тестов** *(2026-08-02)*  
  Удалены `fetch_vk_posts.py`, `vk_test.py`, все JSON файлы

- [x] **Упростить VK тестирование** *(2026-08-02)*  
  VK парсер работает напрямую без промежуточных JSON

- [x] **VK парсинг через API** *(2026-07-31)*  
  Интеграция `vk_parser.py` в Pipeline

- [x] **Рефакторинг AI-клиента** *(2026-07-20)*  
  3 простых промпта вместо JSON, 19/19 правильных на тестах

---

## 🎯 Roadmap

### v1.0 — MVP (current)
- ✅ Парсинг Telegram + VK
- ✅ AI-фильтрация (accept → rewrite → duplicate)
- ✅ Публикация в канал по расписанию
- ⏳ Production-ready конфигурация

### v1.1 — Stability
- Обработка ошибок API (VK, Telegram, Ollama)
- Логирование AI-решений
- Мониторинг и алерты
- Индексы в БД

### v1.2 — Automation
- Web-интерфейс для модерации
- Telegram-бот для управления
- Автоматические отчёты (статистика)

### v2.0 — Scale
- Fine-tuning модели на собранных данных
- Поддержка Instagram
- Multi-языковая поддержка (EN)
- A/B тесты промптов

---

*Последнее обновление: 2026-08-02*
