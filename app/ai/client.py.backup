import asyncio
import logging
import re

from ollama import chat

from app.config import OLLAMA_MODEL

logger = logging.getLogger("basket")

BASKETBALL_KEYWORDS = {
    "баскетбол", "турнир", "матч", "игра", "игру", "игры", "игр",
    "команда", "команду", "команды",
    "лига", "лигу", "лиги",
    "чемпионат", "финал", "полуфинал", "четвертьфинал",
    "очко", "очка", "очков",
    "побед", "победитель", "победа",
    "поражени", "счет", "счёт",
    "тренер", "игрок", "игрока", "игроков",
    "сезон", "сезона",
    "плей-офф", "плейофф",
    "тренировк", "бросок", "броска",
    "nba", "3x3", "3×3", "3х3",
    "благотворительн", "регистраци", "заявк",
    "участие", "принять участие", "приглашаем",
    "стритбол", "корм", "приют",
}

ACCEPT_PROMPT = """
Является ли это сообщением об организуемом самим автором спортивном мероприятии?

YES — автор проводит турнир, открывает регистрацию, собирает заявки, приглашает команды, организует лагерь или мастер-класс.

NO — во всех остальных случаях, включая:
• автор едет/едем/выезжает/отправляется на турнир в другой город
• автор участвует в чужом турнире
• автор играет матч против другой команды
• автор публикует результаты, фото, расписание своих игр
• автор благодарит организаторов, зовёт болельщиков
• поздравления, мемы, реклама, мотивация

Ключевой признак NO: автор упоминает ЧУЖОЙ турнир, куда он едет или где участвует. Слова "едем в", "выезжаем в", "отправляемся на", "участвуем в" + название города = NO.

YES только когда автор САМ принимает заявки и проводит турнир на своей площадке.

Если есть хоть малейшее сомнение — NO.

Ответь только YES или NO.
"""

REWRITE_PROMPT = """
Ты редактор большого Telegram-канала.

Твоя задача — не пересказать текст. Твоя задача — написать новый короткий пост.

Пиши так, будто это публикация популярного Telegram-канала.

Формат ВСЕГДА такой:

Первая строка — короткий заголовок с эмодзи 🏀.

Вторая строка — 📅 дата | ⏰ время | 📍 место

Третья строка — 📝 Заявки: контакт

Если дедлайн есть — четвёртая строка: 📆 До ...

Если какого-то поля нет — не выдумывай его.

Полностью удаляй:
• длинные списки, перечни товаров, правила участия
• историю, рекламу, благодарности, описание атмосферы, эмоции, повторы

Если список длиннее трёх пунктов — удали полностью. Не сокращай. Не пересказывай.

Не меняй факты. Не добавляй свои мысли.

Максимум четыре строки.

Пример:

Исходный текст:
🏀 Grizzly снова организует турнир ради доброго дела! 12 июля проведём мужской турнир 3×3 в помощь приюту «Ржевка». 📅 12 июля ⏰ 12:00 📍 Баскетбольная площадка Московский проспект, 202. Взнос — любой корм от 2 кг. Список кормов: ... Заявки @Vladislav_Sharapa до 10 июля 23:59.

Правильный ответ:
🏀 Grizzly снова организует турнир ради доброго дела!

📅 12 июля | ⏰ 12:00 | 📍 Баскетбольная площадка Московский проспект, 202

📝 Заявки: @Vladislav_Sharapa

📆 До 10 июля 23:59

---

Теперь перепиши следующий текст.
"""

DUPLICATE_PROMPT = """
Ты сравниваешь новость с ранее опубликованными. Ответь YES если то же самое событие/турнир. Ответь NO если новое.

История:
{history}

Новость:
{text}

Ответь только YES или NO.
"""


def has_basketball_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in BASKETBALL_KEYWORDS)


class AIClient:

    def __init__(self):
        self.model = OLLAMA_MODEL

    async def _ask(self, system: str, user: str, num_predict: int | None = None) -> str:
        options = {
            "temperature": 0,
            "top_p": 0.9,
        }
        if num_predict is not None:
            options["num_predict"] = num_predict
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": user})

            response = await asyncio.to_thread(
                chat,
                model=self.model,
                messages=messages,
                options=options,
            )
            return response["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return ""

    async def _accept(self, text: str) -> bool:
        raw = await self._ask(ACCEPT_PROMPT, text, num_predict=10)
        return raw == "YES"

    async def _rewrite(self, text: str) -> str:
        raw = await self._ask(REWRITE_PROMPT, text, num_predict=120)
        if not raw:
            return text
        return self._clean(raw)

    async def _is_duplicate(self, text: str, history: list[str]) -> bool:
        if not history:
            return False
        recent = "\n---\n".join(history[-20:])
        prompt = DUPLICATE_PROMPT.format(history=recent, text=text)
        raw = await self._ask("", prompt, num_predict=10)
        return raw == "YES"

    def _clean(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _skip(self) -> dict:
        return {
            "accept": False,
            "duplicate": False,
            "importance": 3,
            "category": "other",
            "rewritten_text": "",
        }

    async def analyze(self, text: str, history: list[str]) -> dict:
        text = text[:1500]

        if not has_basketball_keywords(text):
            return self._skip()

        if not await self._accept(text):
            return self._skip()

        rewritten = await self._rewrite(text)

        if await self._is_duplicate(rewritten, history):
            return {
                "accept": True,
                "duplicate": True,
                "importance": 3,
                "category": "other",
                "rewritten_text": rewritten,
            }

        return {
            "accept": True,
            "duplicate": False,
            "importance": 3,
            "category": "match_announce",
            "rewritten_text": rewritten,
        }
