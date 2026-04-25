import json
import os
import sys

if not os.path.exists("config.json"):
    print("конфиг не найден")
    sys.exit(1)

with open("config.json", "r", encoding="utf-8") as file:
    config_data = json.load(file)

BOT_TOKEN = config_data.get("bot_token")
if not BOT_TOKEN or BOT_TOKEN == "BOTFATHER_TOKEN":
    print("нету токена")
    sys.exit(1)

YANDEX_TOKEN = config_data.get("yandex_token", "TOKEN")
PROXIES = config_data.get("proxies", [])
DB_NAME = config_data.get("db_name", "users.json")