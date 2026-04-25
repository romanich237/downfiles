import json
import os
import datetime
import asyncio
from config import DB_NAME

def read_db():
    """читает JSON файла"""
    if not os.path.exists(DB_NAME):
        return {"users": {}, "downloads": []}
    
    with open(DB_NAME, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return {"users": {}, "downloads": []}

def write_db(data):
    """Запись данных"""
    with open(DB_NAME, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

async def init_db():
    """создание бд"""
    if not os.path.exists(DB_NAME):
        write_db({"users": {}, "downloads": []})

async def add_user(user_id: int, username: str):
    """добавление юзера в бд"""
    def logic():
        data = read_db()
        user_key = str(user_id)
        if user_key not in data["users"]:
            data["users"][user_key] = {
                "username": username,
                "joined_at": str(datetime.datetime.now())
            }
            write_db(data)
    
    await asyncio.to_thread(logic)

async def log_download(user_id: int, url: str):
    """запись лога загрузки"""
    def logic():
        data = read_db()
        data["downloads"].append({
            "user_id": user_id,
            "url": url,
            "time": str(datetime.datetime.now())
        })
        write_db(data)
        
    await asyncio.to_thread(logic)