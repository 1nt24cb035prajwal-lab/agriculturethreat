from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.environ.get("AGRI_DATABASE_PATH", BASE_DIR / "agriculture.sqlite3"))
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
PASSWORD_ITERATIONS = 310_000


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS farmers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                mobile TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                phone_verified INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id INTEGER NOT NULL UNIQUE REFERENCES farmers(id) ON DELETE CASCADE,
                profile_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS farmer_sessions (
                token_hash TEXT PRIMARY KEY,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
                activity_type TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS activity_farmer_created_idx
                ON activity(farmer_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS disease_images (
                id TEXT PRIMARY KEY,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                media_type TEXT NOT NULL,
                image_data BLOB NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )
        farmer_columns = {row["name"] for row in connection.execute("PRAGMA table_info(farmers)")}
        if "phone_verified" not in farmer_columns:
            connection.execute("ALTER TABLE farmers ADD COLUMN phone_verified INTEGER NOT NULL DEFAULT 0")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), PASSWORD_ITERATIONS)
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_farmer(full_name: str, mobile: str, email: str, password: str, profile: dict[str, Any]) -> dict[str, Any]:
    now = int(time.time())
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO farmers (full_name, mobile, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (full_name, mobile, email, hash_password(password), now),
        )
        farmer_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO farms (farmer_id, profile_json, updated_at) VALUES (?, ?, ?)",
            (farmer_id, json.dumps(profile), now),
        )
        connection.execute(
            "INSERT INTO activity (farmer_id, activity_type, details_json, created_at) VALUES (?, ?, ?, ?)",
            (farmer_id, "account_created", json.dumps({"phoneVerified": False}), now),
        )
        row = connection.execute("SELECT id, full_name, mobile, email FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
    return farmer_public(row)


def get_farmer_by_login(identifier: str) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            "SELECT * FROM farmers WHERE lower(email) = lower(?) OR mobile = ? LIMIT 1",
            (identifier, identifier),
        ).fetchone()


def farmer_public(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"F-{row['id']:06d}" if isinstance(row["id"], int) else str(row["id"]),
        "name": row["full_name"],
        "mobile": row["mobile"],
        "email": row["email"],
        "phoneVerified": bool(row["phone_verified"]) if "phone_verified" in row.keys() else False,
    }


def create_session(farmer_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with connect() as connection:
        connection.execute("DELETE FROM farmer_sessions WHERE expires_at < ?", (int(time.time()),))
        connection.execute(
            "INSERT INTO farmer_sessions (token_hash, farmer_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, farmer_id, int(time.time()) + SESSION_TTL_SECONDS),
        )
    return token


def get_farmer_for_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with connect() as connection:
        row = connection.execute(
            "SELECT f.id, f.full_name, f.mobile, f.email FROM farmer_sessions s "
            "JOIN farmers f ON f.id = s.farmer_id WHERE s.token_hash = ? AND s.expires_at > ?",
            (token_hash, int(time.time())),
        ).fetchone()
    return farmer_public(row) if row else None


def delete_session(token: str | None) -> None:
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with connect() as connection:
            connection.execute("DELETE FROM farmer_sessions WHERE token_hash = ?", (token_hash,))


def get_farm(farmer_id: str) -> dict[str, Any]:
    numeric_id = int(farmer_id.removeprefix("F-"))
    with connect() as connection:
        row = connection.execute("SELECT profile_json FROM farms WHERE farmer_id = ?", (numeric_id,)).fetchone()
    return json.loads(row["profile_json"]) if row else {}


def save_farm(farmer_id: str, profile: dict[str, Any]) -> None:
    numeric_id = int(farmer_id.removeprefix("F-"))
    now = int(time.time())
    with connect() as connection:
        connection.execute(
            "INSERT INTO farms (farmer_id, profile_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(farmer_id) DO UPDATE SET profile_json = excluded.profile_json, updated_at = excluded.updated_at",
            (numeric_id, json.dumps(profile), now),
        )


def record_activity(farmer_id: str, activity_type: str, details: dict[str, Any]) -> None:
    numeric_id = int(farmer_id.removeprefix("F-"))
    with connect() as connection:
        connection.execute(
            "INSERT INTO activity (farmer_id, activity_type, details_json, created_at) VALUES (?, ?, ?, ?)",
            (numeric_id, activity_type, json.dumps(details), int(time.time())),
        )


def get_activity(farmer_id: str, limit: int = 100) -> list[dict[str, Any]]:
    numeric_id = int(farmer_id.removeprefix("F-"))
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, activity_type, details_json, created_at FROM activity "
            "WHERE farmer_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (numeric_id, limit),
        ).fetchall()
    return [
        {"id": row["id"], "type": row["activity_type"], "details": json.loads(row["details_json"]), "createdAt": row["created_at"]}
        for row in rows
    ]


def store_disease_image(farmer_id: str, filename: str, media_type: str, image_data: bytes) -> str:
    numeric_id = int(farmer_id.removeprefix("F-"))
    image_id = secrets.token_urlsafe(18)
    with connect() as connection:
        connection.execute(
            "INSERT INTO disease_images (id, farmer_id, filename, media_type, image_data, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (image_id, numeric_id, Path(filename).name[:255], media_type, image_data, int(time.time())),
        )
    return image_id


def get_disease_image(farmer_id: str, image_id: str) -> dict[str, Any] | None:
    numeric_id = int(farmer_id.removeprefix("F-"))
    with connect() as connection:
        row = connection.execute(
            "SELECT filename, media_type, image_data FROM disease_images WHERE id = ? AND farmer_id = ?",
            (image_id, numeric_id),
        ).fetchone()
    if not row:
        return None
    return {"filename": row["filename"], "mediaType": row["media_type"], "imageData": row["image_data"]}


initialize_database()
