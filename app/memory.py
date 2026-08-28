import sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from .config import settings

class Memory:
    def __init__(self, path=settings.sqlite_path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,user_id TEXT,created_at TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,thread_id TEXT,user_id TEXT,role TEXT,content TEXT,created_at TEXT)")
        self.db.commit()
    def create(self, user_id):
        tid = str(uuid.uuid4()); self.db.execute("INSERT INTO sessions VALUES(?,?,?)",(tid,user_id,datetime.now(timezone.utc).isoformat())); self.db.commit(); return tid
    def sessions(self, user_id):
        return [{"thread_id": r[0], "created_at": r[1]} for r in self.db.execute("SELECT id,created_at FROM sessions WHERE user_id=? ORDER BY created_at DESC",(user_id,))]
    def add(self, thread_id,user_id,role,content):
        self.db.execute("INSERT INTO messages(thread_id,user_id,role,content,created_at) VALUES(?,?,?,?,?)",(thread_id,user_id,role,content,datetime.now(timezone.utc).isoformat())); self.db.commit()
    def history(self, thread_id, limit=12):
        rows=self.db.execute("SELECT role,content FROM messages WHERE thread_id=? ORDER BY id DESC LIMIT ?",(thread_id,limit)).fetchall()
        return list(reversed(rows))

    def has_session(self, user_id, thread_id):
        return self.db.execute(
            "SELECT 1 FROM sessions WHERE id=? AND user_id=?",
            (thread_id, user_id),
        ).fetchone() is not None
