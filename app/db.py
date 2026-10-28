import aiosqlite
from pathlib import Path
from typing import Optional, List

from app.models import Message, Source, Feedback, MessageStatus

DB_PATH = Path("data/survey.db")

async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE,
                username TEXT,
                title TEXT,
                paused INTEGER DEFAULT 0
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                source_tg_id INTEGER,
                tg_message_id INTEGER,
                text TEXT,
                links TEXT,
                features TEXT,
                score INTEGER,
                status TEXT DEFAULT 'new',
                hash TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY,
                message_id INTEGER,
                action TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages (id)
            )
        """)
        await db.commit()

async def is_duplicate(hash_val: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM messages WHERE hash = ?", (hash_val,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def save_message(msg: Message) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO messages (source_tg_id, tg_message_id, text, links, features, score, status, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg.source_tg_id, msg.tg_message_id, msg.text, msg.links, 
              msg.features, msg.score, msg.status, msg.hash))
        await db.commit()
        return cursor.lastrowid

async def update_message_status(msg_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE messages SET status = ? WHERE id = ?", (status, msg_id))
        await db.commit()

async def save_feedback(message_id: int, action: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO feedback (message_id, action) VALUES (?, ?)", (message_id, action))
        await db.commit()

async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM messages") as cursor:
            total = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM messages WHERE status = ?", (MessageStatus.OPENED,)) as cursor:
            opened = (await cursor.fetchone())[0]
    return {"total": total, "opened": opened}