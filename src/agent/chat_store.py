import sqlite3
from pathlib import Path
from datetime import datetime
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parent.parent.parent / ".data" / "chat" / "chat_history.db"


class ChatStore:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)

    def create_session(self, title="Novo Chat"):
        session_id = str(uuid4())
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now, now),
            )
        return session_id

    def save_message(self, session_id: str, role: str, content: str):
        now = datetime.now().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )

    def load_messages(self, session_id: str):
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]

    def list_sessions(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT id, title, created_at FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        return [{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows]

    def delete_session(self, session_id: str):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def rename_session(self, session_id: str, title: str):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (title, session_id),
            )

    def count_messages(self, session_id: str) -> int:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row[0] if row else 0
