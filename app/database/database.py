import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "severus.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()

    # Users Table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Chat Messages Table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # User Memories Table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS user_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            category TEXT NOT NULL DEFAULT 'preference',
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, key)
        )
    """)

    # Uploaded Documents / Vector Store Metadata Table (Phase 14 RAG)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS user_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            storage_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration checks: Add user_id column if table existed without it
    cursor = connection.cursor()

    # Check chat_messages table columns
    cursor.execute("PRAGMA table_info(chat_messages)")
    cols = [col["name"] for col in cursor.fetchall()]
    if "user_id" not in cols:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN user_id INTEGER DEFAULT 1")

    # Check user_memories table columns
    cursor.execute("PRAGMA table_info(user_memories)")
    cols = [col["name"] for col in cursor.fetchall()]
    if "user_id" not in cols:
        cursor.execute("ALTER TABLE user_memories ADD COLUMN user_id INTEGER DEFAULT 1")

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_tables()