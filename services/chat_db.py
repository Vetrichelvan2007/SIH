import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_FILE = Path(__file__).parent.parent / "chats.db"

def get_connection():
    """Establishes and returns SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database tables and WAL mode."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        
        # Create chats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                model_used TEXT,
                route TEXT,
                response_time REAL,
                order_index INTEGER NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats (chat_id) ON DELETE CASCADE
            );
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chats_updated_at ON chats(updated_at DESC);")
        conn.commit()

def generate_timestamp() -> str:
    """Generates ISO 8601 timestamp string."""
    return datetime.now(timezone.utc).isoformat()

def auto_generate_title(content: str) -> str:
    """Generates simple title from first user message limited to ~30-40 characters."""
    clean_text = " ".join(content.strip().split())
    if len(clean_text) <= 35:
        return clean_text if clean_text else "New Chat"
    return clean_text[:35].rstrip() + "..."

def get_all_chats() -> List[Dict[str, Any]]:
    """
    Returns list of all saved chats ordered by updated_at descending.
    Each item includes chat_id, title, created_at, updated_at, and message count.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.chat_id, c.title, c.created_at, c.updated_at,
                   COUNT(m.message_id) AS message_count
            FROM chats c
            LEFT JOIN messages m ON c.chat_id = m.chat_id
            GROUP BY c.chat_id
            ORDER BY c.updated_at DESC;
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_chat(chat_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns complete chat dictionary with all messages ordered by order_index ASC.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, title, created_at, updated_at FROM chats WHERE chat_id = ?;", (chat_id,))
        chat_row = cursor.fetchone()
        if not chat_row:
            return None
        
        cursor.execute("""
            SELECT message_id, role, content, timestamp, model_used, route, response_time
            FROM messages
            WHERE chat_id = ?
            ORDER BY order_index ASC;
        """, (chat_id,))
        msg_rows = cursor.fetchall()
        
        chat_dict = dict(chat_row)
        messages = []
        for msg in msg_rows:
            m = {
                "message_id": msg["message_id"],
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"]
            }
            if msg["model_used"] is not None:
                m["model_used"] = msg["model_used"]
            if msg["route"] is not None:
                m["route"] = msg["route"]
            if msg["response_time"] is not None:
                m["response_time"] = msg["response_time"]
            messages.append(m)
            
        chat_dict["messages"] = messages
        return chat_dict

def create_chat(chat_id: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new empty chat entry in the database."""
    init_db()
    c_id = chat_id or str(uuid.uuid4())
    t_title = title if title and title.strip() else "New Chat"
    now = generate_timestamp()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO chats (chat_id, title, created_at, updated_at) VALUES (?, ?, ?, ?);",
            (c_id, t_title, now, now)
        )
        conn.commit()
    
    return {
        "chat_id": c_id,
        "title": t_title,
        "created_at": now,
        "updated_at": now,
        "messages": []
    }

def add_message(
    chat_id: str,
    role: str,
    content: str,
    message_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    model_used: Optional[str] = None,
    route: Optional[str] = None,
    response_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Appends a message to an existing or new chat.
    Auto-updates chat updated_at and auto-generates title if it is the first user message.
    """
    init_db()
    now = generate_timestamp()
    m_id = message_id or str(uuid.uuid4())
    m_time = timestamp or now
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if chat exists
        cursor.execute("SELECT chat_id, title FROM chats WHERE chat_id = ?;", (chat_id,))
        chat_row = cursor.fetchone()
        
        if not chat_row:
            # First message in chat - auto title if role is user
            title = auto_generate_title(content) if role == "user" else "New Chat"
            cursor.execute(
                "INSERT INTO chats (chat_id, title, created_at, updated_at) VALUES (?, ?, ?, ?);",
                (chat_id, title, now, now)
            )
        else:
            current_title = chat_row["title"]
            # If title is default "New Chat" or "New Conversation" and role is user, update title
            if role == "user" and (current_title in ["New Chat", "New Conversation", ""]):
                new_title = auto_generate_title(content)
                cursor.execute(
                    "UPDATE chats SET title = ?, updated_at = ? WHERE chat_id = ?;",
                    (new_title, now, chat_id)
                )
            else:
                cursor.execute("UPDATE chats SET updated_at = ? WHERE chat_id = ?;", (now, chat_id))
        
        # Determine order index
        cursor.execute("SELECT COALESCE(MAX(order_index), 0) + 1 AS next_idx FROM messages WHERE chat_id = ?;", (chat_id,))
        next_idx = cursor.fetchone()["next_idx"]
        
        cursor.execute("""
            INSERT INTO messages (message_id, chat_id, role, content, timestamp, model_used, route, response_time, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (m_id, chat_id, role, content, m_time, model_used, route, response_time, next_idx))
        
        conn.commit()
    
    msg_dict = {
        "message_id": m_id,
        "role": role,
        "content": content,
        "timestamp": m_time
    }
    if model_used is not None:
        msg_dict["model_used"] = model_used
    if route is not None:
        msg_dict["route"] = route
    if response_time is not None:
        msg_dict["response_time"] = response_time
        
    return msg_dict

def update_chat_title(chat_id: str, new_title: str) -> Optional[Dict[str, Any]]:
    """Renames an existing chat session."""
    init_db()
    now = generate_timestamp()
    clean_title = new_title.strip() if new_title and new_title.strip() else "Untitled Chat"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE chats SET title = ?, updated_at = ? WHERE chat_id = ?;", (clean_title, now, chat_id))
        if cursor.rowcount == 0:
            return None
        conn.commit()
    
    return get_chat(chat_id)

def delete_chat(chat_id: str) -> bool:
    """Deletes a chat session and associated messages."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE chat_id = ?;", (chat_id,))
        cursor.execute("DELETE FROM chats WHERE chat_id = ?;", (chat_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted

def get_trimmed_model_messages(chat_id: str, max_messages: int = 15) -> List[Dict[str, str]]:
    """
    Retrieves the last N messages formatted for Ollama / LLM prompt context:
    [{"role": "user"|"assistant", "content": "..."}, ...]
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content
            FROM (
                SELECT role, content, order_index
                FROM messages
                WHERE chat_id = ?
                ORDER BY order_index DESC
                LIMIT ?
            )
            ORDER BY order_index ASC;
        """, (chat_id, max_messages))
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
