"""Database manager for the AI Job Applicant Bot."""

import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """SQLite database manager with basic CRUD helpers."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.initialized = False
            return cls._instance

    def __init__(self, db_path: str = "db/application_data.db", max_connections: int = 5) -> None:
        if self.initialized:
            return
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_connections = max_connections
        self.connection_pool: List[sqlite3.Connection] = []
        self.initialized = True
        self._initialize_database()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def _initialize_database(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    settings TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS resumes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    parsed_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    job_board TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'new',
                    match_score REAL DEFAULT 0,
                    applied_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS applications (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    resume_id TEXT NOT NULL,
                    cover_letter_path TEXT,
                    status TEXT DEFAULT 'pending',
                    applied_at TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_received_at TIMESTAMP,
                    response_type TEXT,
                    notes TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (resume_id) REFERENCES resumes(id)
                )
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def _get_connection(self) -> sqlite3.Connection:
        if self.connection_pool:
            conn = self.connection_pool.pop()
            try:
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                pass
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn

    def _release_connection(self, conn: sqlite3.Connection) -> None:
        if len(self.connection_pool) < self.max_connections:
            self.connection_pool.append(conn)
        else:
            conn.close()

    # ------------------------------------------------------------------
    # Generic query helpers
    # ------------------------------------------------------------------
    def execute_query(self, query: str, params: tuple = (), fetchone: bool = False):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                conn.commit()
                return cursor.lastrowid
            return cursor.fetchone() if fetchone else cursor.fetchall()
        except Exception as exc:
            conn.rollback()
            logger.error("Database error: %s", exc)
            raise
        finally:
            self._release_connection(conn)

    # ------------------------------------------------------------------
    # High level API
    # ------------------------------------------------------------------
    def create_user(self, user_id: str, email: str, password_hash: str) -> bool:
        try:
            self.execute_query(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, email, password_hash),
            )
            return True
        except Exception:
            logger.exception("Failed to create user")
            return False

    def get_user(self, user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if user_id:
            row = self.execute_query("SELECT * FROM users WHERE id = ?", (user_id,), fetchone=True)
        elif email:
            row = self.execute_query("SELECT * FROM users WHERE email = ?", (email,), fetchone=True)
        else:
            return None
        return dict(row) if row else None

    def save_resume(self, resume_id: str, user_id: str, file_path: str, parsed_data: Dict[str, Any]) -> bool:
        try:
            self.execute_query(
                """
                INSERT INTO resumes (id, user_id, file_path, parsed_data)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET file_path = ?, parsed_data = ?, last_updated = CURRENT_TIMESTAMP
                """,
                (resume_id, user_id, file_path, json.dumps(parsed_data), file_path, json.dumps(parsed_data)),
            )
            return True
        except Exception:
            logger.exception("Failed to save resume")
            return False

    def get_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        row = self.execute_query("SELECT * FROM resumes WHERE id = ?", (resume_id,), fetchone=True)
        if row:
            data = dict(row)
            if data.get("parsed_data"):
                data["parsed_data"] = json.loads(data["parsed_data"])
            return data
        return None

    def save_job(self, job_data: Dict[str, Any]) -> bool:
        try:
            columns = ", ".join(job_data.keys())
            placeholders = ", ".join(["?"] * len(job_data))
            values = tuple(job_data.values())
            self.execute_query(f"INSERT INTO jobs ({columns}) VALUES ({placeholders})", values)
            return True
        except Exception:
            logger.exception("Failed to save job")
            return False

    def update_job(self, job_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            set_clause = ", ".join([f"{k} = ?" for k in update_data])
            values = tuple(update_data.values()) + (job_id,)
            self.execute_query(
                f"UPDATE jobs SET {set_clause}, last_updated = CURRENT_TIMESTAMP WHERE id = ?",
                values,
            )
            return True
        except Exception:
            logger.exception("Failed to update job")
            return False

    def backup_database(self, backup_path: Optional[str] = None) -> str:
        if backup_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"db/backups/backup_{timestamp}.db"
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        conn = self._get_connection()
        try:
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            return backup_path
        finally:
            self._release_connection(conn)

