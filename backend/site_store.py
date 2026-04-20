from __future__ import annotations

import hashlib
import hmac
import math
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException

DB_PATH = Path(__file__).with_name("site_data.db")
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60


def _now_ts() -> int:
    return int(time.time())


@contextmanager
def db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    _, candidate = _hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, password_hash)


def _normalize_username(username: str) -> str:
    return username.strip()


def _fallback_cover(album_id: str, cover: str = "") -> str:
    return cover or f"/api/comics/{album_id}/cover"


def _serialize_user(row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "is_admin": bool(row["is_admin"]),
        "created_at": row["created_at"],
    }


def _serialize_favorite(row) -> dict:
    return {
        "id": row["album_id"],
        "album_id": row["album_id"],
        "title": row["title"] or row["album_id"],
        "author": row["author"] or "",
        "cover": _fallback_cover(row["album_id"], row["cover"] or ""),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _serialize_history(row) -> dict:
    return {
        "id": row["album_id"],
        "album_id": row["album_id"],
        "title": row["title"] or row["album_id"],
        "author": row["author"] or "",
        "cover": _fallback_cover(row["album_id"], row["cover"] or ""),
        "visited_at": row["last_read_at"],
        "last_read_at": row["last_read_at"],
        "view_count": row["view_count"],
        "last_photo_id": row["last_photo_id"],
        "last_photo_title": row["last_photo_title"] or "",
        "last_chapter_sort": row["last_chapter_sort"],
        "last_page": row["last_page"],
        "total_pages": row["total_pages"],
    }


def _serialize_chapter_progress(row) -> dict:
    return {
        "photo_id": row["photo_id"],
        "chapter_title": row["chapter_title"] or "",
        "chapter_sort": row["chapter_sort"],
        "last_page": row["last_page"],
        "total_pages": row["total_pages"],
        "updated_at": row["updated_at"],
    }


def init_site_storage() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db_conn() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                album_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '',
                cover TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, album_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                user_id INTEGER NOT NULL,
                album_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '',
                cover TEXT NOT NULL DEFAULT '',
                last_read_at INTEGER NOT NULL,
                view_count INTEGER NOT NULL DEFAULT 1,
                last_photo_id TEXT,
                last_photo_title TEXT NOT NULL DEFAULT '',
                last_chapter_sort INTEGER,
                last_page INTEGER NOT NULL DEFAULT 0,
                total_pages INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, album_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chapter_progress (
                user_id INTEGER NOT NULL,
                album_id TEXT NOT NULL,
                photo_id TEXT NOT NULL,
                chapter_title TEXT NOT NULL DEFAULT '',
                chapter_sort INTEGER,
                last_page INTEGER NOT NULL DEFAULT 0,
                total_pages INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, photo_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorites_user_updated ON favorites(user_id, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_user_updated ON history(user_id, last_read_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_progress_user_album_updated ON chapter_progress(user_id, album_id, updated_at DESC)"
        )

        admin = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            ("admin",),
        ).fetchone()
        if not admin:
            now = _now_ts()
            salt_hex, password_hash = _hash_password("wyq666")
            conn.execute(
                """
                INSERT INTO users (username, password_salt, password_hash, is_admin, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                ("admin", salt_hex, password_hash, now, now),
            )


def create_user(username: str, password: str, is_admin: bool = False) -> dict:
    normalized = _normalize_username(username)
    if len(normalized) < 3:
        raise HTTPException(400, "用户名至少 3 位")
    if len(password) < 6:
        raise HTTPException(400, "密码至少 6 位")

    now = _now_ts()
    salt_hex, password_hash = _hash_password(password)
    try:
        with db_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_salt, password_hash, is_admin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (normalized, salt_hex, password_hash, int(is_admin), now, now),
            )
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
            return _serialize_user(row)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "用户名已存在")


def list_users() -> list[dict]:
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY is_admin DESC, username ASC"
        ).fetchall()
        return [_serialize_user(row) for row in rows]


def authenticate_user(username: str, password: str) -> Optional[dict]:
    normalized = _normalize_username(username)
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (normalized,),
        ).fetchone()
        if not row or not _verify_password(password, row["password_salt"], row["password_hash"]):
            return None

        token = secrets.token_urlsafe(32)
        now = _now_ts()
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, row["id"], now, now + SESSION_TTL_SECONDS),
        )
        return {"token": token, "user": _serialize_user(row)}


def extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    raw = authorization.strip()
    if not raw:
        return None
    if " " not in raw:
        return raw
    scheme, token = raw.split(" ", 1)
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def delete_session(token: str) -> None:
    with db_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def get_user_by_token(token: str) -> Optional[dict]:
    now = _now_ts()
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (token, now),
        ).fetchone()
        if row:
            return _serialize_user(row)
        conn.execute(
            "DELETE FROM sessions WHERE token = ? OR expires_at <= ?",
            (token, now),
        )
        return None


def require_current_user(authorization: Optional[str] = Header(None)) -> dict:
    token = extract_token(authorization)
    if not token:
        raise HTTPException(401, "未登录")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, "登录状态已失效")
    return user


def require_admin_user(authorization: Optional[str] = Header(None)) -> dict:
    user = require_current_user(authorization)
    if not user["is_admin"]:
        raise HTTPException(403, "需要管理员权限")
    return user


def list_favorites(user_id: int, page: int, page_size: int) -> dict:
    offset = (page - 1) * page_size
    with db_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS total FROM favorites WHERE user_id = ?",
            (user_id,),
        ).fetchone()["total"]
        rows = conn.execute(
            """
            SELECT *
            FROM favorites
            WHERE user_id = ?
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, page_size, offset),
        ).fetchall()
    return {
        "items": [_serialize_favorite(row) for row in rows],
        "total": total,
        "page_count": math.ceil(total / page_size) if total else 0,
    }


def add_favorite(
    user_id: int,
    album_id: str,
    title: str = "",
    author: str = "",
    cover: str = "",
) -> dict:
    now = _now_ts()
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO favorites (user_id, album_id, title, author, cover, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, album_id) DO UPDATE SET
                title = CASE WHEN excluded.title <> '' THEN excluded.title ELSE favorites.title END,
                author = CASE WHEN excluded.author <> '' THEN excluded.author ELSE favorites.author END,
                cover = CASE WHEN excluded.cover <> '' THEN excluded.cover ELSE favorites.cover END,
                updated_at = excluded.updated_at
            """,
            (user_id, album_id, title, author, cover, now, now),
        )
        row = conn.execute(
            "SELECT * FROM favorites WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        ).fetchone()
    return _serialize_favorite(row)


def remove_favorite(user_id: int, album_id: str) -> bool:
    with db_conn() as conn:
        cur = conn.execute(
            "DELETE FROM favorites WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        )
        return cur.rowcount > 0


def get_favorite_status(user_id: int, album_id: str) -> dict:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM favorites WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        ).fetchone()
    return {"favorited": bool(row), "item": _serialize_favorite(row) if row else None}


def upsert_history(
    user_id: int,
    album_id: str,
    title: str = "",
    author: str = "",
    cover: str = "",
) -> dict:
    now = _now_ts()
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO history (
                user_id, album_id, title, author, cover,
                last_read_at, view_count, last_photo_id, last_photo_title, last_chapter_sort, last_page, total_pages
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, NULL, '', NULL, 0, 0)
            ON CONFLICT(user_id, album_id) DO UPDATE SET
                title = CASE WHEN excluded.title <> '' THEN excluded.title ELSE history.title END,
                author = CASE WHEN excluded.author <> '' THEN excluded.author ELSE history.author END,
                cover = CASE WHEN excluded.cover <> '' THEN excluded.cover ELSE history.cover END,
                last_read_at = excluded.last_read_at,
                view_count = history.view_count + 1
            """,
            (user_id, album_id, title, author, cover, now),
        )
        row = conn.execute(
            "SELECT * FROM history WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        ).fetchone()
    return _serialize_history(row)


def list_history(user_id: int, page: int, page_size: int) -> dict:
    offset = (page - 1) * page_size
    with db_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS total FROM history WHERE user_id = ?",
            (user_id,),
        ).fetchone()["total"]
        rows = conn.execute(
            """
            SELECT *
            FROM history
            WHERE user_id = ?
            ORDER BY last_read_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, page_size, offset),
        ).fetchall()
    return {
        "items": [_serialize_history(row) for row in rows],
        "total": total,
        "page_count": math.ceil(total / page_size) if total else 0,
    }


def remove_history(user_id: int, album_id: str) -> bool:
    with db_conn() as conn:
        conn.execute(
            "DELETE FROM chapter_progress WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        )
        cur = conn.execute(
            "DELETE FROM history WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        )
        return cur.rowcount > 0


def clear_history(user_id: int) -> dict:
    with db_conn() as conn:
        deleted_history = conn.execute(
            "DELETE FROM history WHERE user_id = ?",
            (user_id,),
        ).rowcount
        conn.execute(
            "DELETE FROM chapter_progress WHERE user_id = ?",
            (user_id,),
        )
    return {"cleared": deleted_history}


def save_reading_progress(
    user_id: int,
    album_id: str,
    photo_id: str,
    album_title: str = "",
    album_author: str = "",
    cover: str = "",
    chapter_title: str = "",
    chapter_sort: Optional[int] = None,
    last_page: int = 0,
    total_pages: int = 0,
) -> dict:
    now = _now_ts()
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO chapter_progress (
                user_id, album_id, photo_id, chapter_title, chapter_sort, last_page, total_pages, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, photo_id) DO UPDATE SET
                album_id = excluded.album_id,
                chapter_title = excluded.chapter_title,
                chapter_sort = excluded.chapter_sort,
                last_page = excluded.last_page,
                total_pages = excluded.total_pages,
                updated_at = excluded.updated_at
            """,
            (user_id, album_id, photo_id, chapter_title, chapter_sort, last_page, total_pages, now),
        )
        conn.execute(
            """
            INSERT INTO history (
                user_id, album_id, title, author, cover,
                last_read_at, view_count, last_photo_id, last_photo_title, last_chapter_sort, last_page, total_pages
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, album_id) DO UPDATE SET
                title = CASE WHEN excluded.title <> '' THEN excluded.title ELSE history.title END,
                author = CASE WHEN excluded.author <> '' THEN excluded.author ELSE history.author END,
                cover = CASE WHEN excluded.cover <> '' THEN excluded.cover ELSE history.cover END,
                last_read_at = excluded.last_read_at,
                last_photo_id = excluded.last_photo_id,
                last_photo_title = excluded.last_photo_title,
                last_chapter_sort = excluded.last_chapter_sort,
                last_page = excluded.last_page,
                total_pages = excluded.total_pages
            """,
            (
                user_id,
                album_id,
                album_title,
                album_author,
                cover,
                now,
                photo_id,
                chapter_title,
                chapter_sort,
                last_page,
                total_pages,
            ),
        )
        row = conn.execute(
            "SELECT * FROM history WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        ).fetchone()
    return _serialize_history(row)


def get_reading_state(user_id: int, album_id: str) -> dict:
    with db_conn() as conn:
        history_row = conn.execute(
            "SELECT * FROM history WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        ).fetchone()
        favorite_row = conn.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND album_id = ?",
            (user_id, album_id),
        ).fetchone()
        chapter_rows = conn.execute(
            """
            SELECT *
            FROM chapter_progress
            WHERE user_id = ? AND album_id = ?
            ORDER BY updated_at DESC, COALESCE(chapter_sort, 0) ASC
            """,
            (user_id, album_id),
        ).fetchall()

    chapters = [_serialize_chapter_progress(row) for row in chapter_rows]
    progress_map = {item["photo_id"]: item for item in chapters}
    return {
        "album_id": album_id,
        "is_favorite": bool(favorite_row),
        "history": _serialize_history(history_row) if history_row else None,
        "last_read_photo_id": history_row["last_photo_id"] if history_row else None,
        "chapters": chapters,
        "progress_map": progress_map,
    }
