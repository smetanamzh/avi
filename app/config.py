from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_IDS = os.getenv("CHANNEL_IDS", "").split(",")
CHANNEL_IDS = [ch.strip() for ch in CHANNEL_IDS if ch.strip()]
MY_CHANNEL_ID = os.getenv("MY_CHANNEL_ID")

VK_APP_ID = os.getenv("VK_APP_ID")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_IDS = os.getenv("VK_GROUP_IDS", "").split(",")
VK_GROUP_IDS = [g.strip() for g in VK_GROUP_IDS if g.strip()]

OLLAMA_MODEL = "qwen2.5:7b"

PUBLISH_INTERVAL_MINUTES = int(os.getenv("PUBLISH_INTERVAL_MINUTES", "30"))
PUBLISH_START_HOUR = int(os.getenv("PUBLISH_START_HOUR", "0"))
PUBLISH_END_HOUR = int(os.getenv("PUBLISH_END_HOUR", "24"))

RESET_DB = True