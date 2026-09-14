import re
import logging
from typing import List, Dict, Any, Optional
from app.database.database import get_connection, create_tables

logger = logging.getLogger("severus.memory_service")


class MemoryService:
    """
    Lightweight, persistent Advanced Memory Service using SQLite.
    Stores user preferences, facts, and conversation context across sessions.
    Strictly filters out secrets, passwords, tokens, and API keys.
    Supports user isolation per user_id.
    """

    SECRET_PATTERNS = [
        r'AIzaSy[A-Za-z0-9_-]{33}',                            # Google API Key
        r'sk-[A-Za-z0-9_-]{20,}',                             # OpenAI API Key
        r'\b(bearer|token|access_token|refresh_token)\b\s*[:=\s]\s*[^\s]+', # Auth tokens / Bearer headers
        r'\b(api_key|apikey|secret|password|passwd)\b\s*[:=]\s*[^\s]+',     # Key-value secrets
        r'[A-Za-z0-9+/]{40,}={0,2}',                          # Base64 style credentials / tokens
    ]

    def __init__(self):
        create_tables()

    def contains_secret(self, text: str) -> bool:
        """
        Scans text for sensitive patterns like API keys, passwords, bearer tokens, or secrets.
        Returns True if a secret pattern is matched.
        """
        if not text or not isinstance(text, str):
            return False

        text_lower = text.lower()
        if any(kw in text_lower for kw in ["google_api_key", "tavily_api_key", "sk-", "aizasy", "bearer "]):
            return True

        for pattern in self.SECRET_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def save_memory(self, key: str, value: str, category: str = "preference", user_id: int = 1) -> bool:
        """
        Safely saves or updates a memory key-value pair in SQLite database for a specific user_id.
        Enforces secret filtering before storing.
        """
        if not key or not value:
            return False

        key_clean = key.strip().lower()
        val_clean = value.strip()

        # Secret Guard Enforcement
        if self.contains_secret(key_clean) or self.contains_secret(val_clean):
            logger.warning(f"Memory save blocked for key '{key_clean}': Contains potential secret/credential.")
            return False

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_memories WHERE key = ? AND (user_id = ? OR user_id IS NULL OR user_id = 1)", (key_clean, user_id))
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE user_memories SET value = ?, category = ?, user_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (val_clean, category, user_id, existing["id"])
                )
            else:
                cursor.execute(
                    "INSERT INTO user_memories (user_id, category, key, value) VALUES (?, ?, ?, ?)",
                    (user_id, category, key_clean, val_clean)
                )
            conn.commit()
            conn.close()
            logger.info(f"Saved memory for user {user_id}: {key_clean} = {val_clean}")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False

    def extract_and_save_facts(self, message: str, user_id: int = 1) -> List[str]:
        """
        Lightweight fact extractor. Scans user prompt for preference or fact statements.
        Returns list of saved memory keys.
        """
        if not message or self.contains_secret(message):
            return []

        saved_keys = []
        msg_lower = message.strip()

        # 1. "remember that <fact>"
        rem_match = re.search(r'\bremember\s+that\s+([^\n.,;]+)', msg_lower, re.IGNORECASE)
        if rem_match:
            fact = rem_match.group(1).strip()
            fact_key = f"fact_{abs(hash(fact)) % 10000}"
            if self.save_memory(key=fact_key, value=fact, category="fact", user_id=user_id):
                saved_keys.append(fact_key)

        # 2. "my name is <name>"
        name_match = re.search(r'\bmy\s+name\s+is\s+([A-Za-z0-9_-]+)', msg_lower, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
            if self.save_memory(key="user_name", value=name, category="preference", user_id=user_id):
                saved_keys.append("user_name")

        # 3. "i prefer <preference>"
        pref_match = re.search(r'\bi\s+prefer\s+([^\n.,;]+)', msg_lower, re.IGNORECASE)
        if pref_match:
            pref = pref_match.group(1).strip()
            if self.save_memory(key="user_preference", value=pref, category="preference", user_id=user_id):
                saved_keys.append("user_preference")

        # 4. "my project is called <name>" / "my project name is <name>"
        proj_match = re.search(r'\bmy\s+project\s+(?:name\s+is|is\s+called|is)\s+([A-Za-z0-9_-]+)', msg_lower, re.IGNORECASE)
        if proj_match:
            proj = proj_match.group(1).strip()
            if self.save_memory(key="project_name", value=proj, category="fact", user_id=user_id):
                saved_keys.append("project_name")

        return saved_keys

    def get_relevant_memories(self, query: str = "", user_id: int = 1) -> List[Dict[str, str]]:
        """
        Retrieves active stored memories from SQLite database for specific user_id.
        """
        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT category, key, value, updated_at FROM user_memories WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            ).fetchall()
            conn.close()

            memories = []
            query_words = set(re.findall(r'\w+', query.lower())) if query else set()

            for row in rows:
                item = {
                    "category": row["category"],
                    "key": row["key"],
                    "value": row["value"],
                    "updated_at": str(row["updated_at"])
                }
                if not query_words or any(w in item["key"].lower() or w in item["value"].lower() for w in query_words):
                    memories.append(item)
                elif item["category"] in ["preference", "fact"]:
                    memories.append(item)

            return memories
        except Exception as e:
            logger.error(f"Failed to retrieve memories for user {user_id}: {e}")
            return []

    def get_all_memories(self, user_id: int = 1) -> List[Dict[str, str]]:
        """
        Retrieves all stored memories for a specific user_id.
        """
        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT category, key, value, updated_at FROM user_memories WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            ).fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get all memories for user {user_id}: {e}")
            return []

    def clear_all_memories(self, user_id: int = 1) -> int:
        """
        Clears all stored memories for a specific user_id from SQLite.
        Returns number of deleted memory entries.
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
            count = cursor.rowcount
            conn.commit()
            conn.close()
            logger.info(f"Cleared {count} memory entries for user {user_id}.")
            return count
        except Exception as e:
            logger.error(f"Failed to clear memories for user {user_id}: {e}")
            return 0


memory_service = MemoryService()
