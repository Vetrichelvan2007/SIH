import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_FILE = Path(__file__).parent.parent / "chats.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_state_db():
    """Initializes SQLite database tables for attachments persistence."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                attachment_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content_type TEXT NOT NULL,
                page_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                processed_result_json TEXT NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats (chat_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attachments_chat_id ON attachments(chat_id);")
        conn.commit()

def generate_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

def register_attachment(
    chat_id: str,
    filename: str,
    file_type: str,
    content_type: str,
    result_dict: Dict[str, Any],
    attachment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Registers or updates an attachment for a given conversation (chat_id).
    Stores processed document text, page breakdowns, and vision analyses.
    """
    init_state_db()
    att_id = attachment_id or f"att-{uuid.uuid4().hex[:10]}"
    now = generate_timestamp()
    
    pages = result_dict.get("metadata", {}).get("pages") or result_dict.get("metadata", {}).get("total_pages") or 1
    
    result_json = json.dumps(result_dict)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO attachments 
            (attachment_id, chat_id, filename, file_type, content_type, page_count, created_at, processed_result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (att_id, chat_id, filename, file_type, content_type, pages, now, result_json))
        conn.commit()

    return {
        "attachment_id": att_id,
        "chat_id": chat_id,
        "filename": filename,
        "file_type": file_type,
        "content_type": content_type,
        "page_count": pages,
        "created_at": now,
        "result": result_dict
    }

def get_chat_attachments(chat_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all attachments registered under a specific chat_id ordered by creation time ASC.
    """
    init_state_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT attachment_id, chat_id, filename, file_type, content_type, page_count, created_at, processed_result_json
            FROM attachments
            WHERE chat_id = ?
            ORDER BY created_at ASC;
        """, (chat_id,))
        rows = cursor.fetchall()
        
        result = []
        for r in rows:
            item = dict(r)
            try:
                item["result"] = json.loads(r["processed_result_json"])
            except Exception:
                item["result"] = {}
            del item["processed_result_json"]
            result.append(item)
        return result

def get_attachment_by_id(attachment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single attachment by its attachment_id."""
    init_state_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT attachment_id, chat_id, filename, file_type, content_type, page_count, created_at, processed_result_json
            FROM attachments
            WHERE attachment_id = ?;
        """, (attachment_id,))
        row = cursor.fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["result"] = json.loads(row["processed_result_json"])
        except Exception:
            item["result"] = {}
        del item["processed_result_json"]
        return item

def get_latest_attachment(chat_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent attachment for a given chat_id."""
    init_state_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT attachment_id, chat_id, filename, file_type, content_type, page_count, created_at, processed_result_json
            FROM attachments
            WHERE chat_id = ?
            ORDER BY created_at DESC
            LIMIT 1;
        """, (chat_id,))
        row = cursor.fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["result"] = json.loads(row["processed_result_json"])
        except Exception:
            item["result"] = {}
        del item["processed_result_json"]
        return item

def delete_attachment(attachment_id: str) -> bool:
    """Deletes an attachment from SQLite state."""
    init_state_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM attachments WHERE attachment_id = ?;", (attachment_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
