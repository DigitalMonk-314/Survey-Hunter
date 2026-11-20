import aiosqlite
import json
from pathlib import Path

from app.models import Message, MessageStatus

DB_PATH = Path("data/survey.db")


async def init_db():
    """Создаёт папку data/ и таблицы sources, messages, feedback. Вызывается один раз при старте."""
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
    """Проверяет, есть ли в messages запись с таким хешем. Нужна для дедупликации до сохранения."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        async with db.execute("SELECT 1 FROM messages WHERE hash = ?", (hash_val,)) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def save_message(msg: Message) -> int:
    """Вставляет сообщение в messages. При дубликате хеша тихо игнорирует. Возвращает id записи."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        cursor = await db.execute("""
            INSERT OR IGNORE INTO messages
            (source_tg_id, tg_message_id, text, links, features, score, status, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg.source_tg_id, msg.tg_message_id, msg.text, msg.links,
              msg.features, msg.score, msg.status, msg.hash))
        await db.commit()
        return cursor.lastrowid


async def update_message_status(msg_id: int, status: str):
    """Меняет статус сообщения: new → sent → opened / skipped / spam. Вызывается из notifier.py."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("UPDATE messages SET status = ? WHERE id = ?", (status, msg_id))
        await db.commit()


async def save_feedback(message_id: int, action: str):
    """Записывает действие пользователя (opened/skipped/spam) в feedback. Нужна для аналитики."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("INSERT INTO feedback (message_id, action) VALUES (?, ?)", (message_id, action))
        await db.commit()


async def get_stats() -> dict:
    """Возвращает счётчики сообщений по всем статусам. Используется командой /stats."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        async with db.execute("SELECT COUNT(*) FROM messages") as cursor:
            total = (await cursor.fetchone())[0]
        stats = {"total": total}
        for st in [MessageStatus.NEW, MessageStatus.SENT, MessageStatus.OPENED,
                   MessageStatus.SKIPPED, MessageStatus.SPAM]:
            async with db.execute("SELECT COUNT(*) FROM messages WHERE status = ?", (st,)) as cursor:
                stats[st] = (await cursor.fetchone())[0]
    return stats


async def get_message(msg_id: int):
    """Читает сообщение по id. links и features парсит из JSON в list/dict. Нужна notifier.py."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        async with db.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "source_tg_id": row[1],
                "tg_message_id": row[2],
                "text": row[3],
                "links": json.loads(row[4]) if row[4] else [],
                "features": json.loads(row[5]) if row[5] else {},
                "score": row[6],
                "status": row[7],
                "hash": row[8],
                "created_at": row[9],
            }