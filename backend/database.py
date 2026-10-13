import hashlib
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from backend.auth import hash_password, verify_password as verify_hash_password


class DatabaseManager:
    def __init__(self, db_path: str = "utm_client_data.db"):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT NOT NULL DEFAULT 'operator',
                    company_name TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    sample_id TEXT NOT NULL,
                    material_grade TEXT,
                    standard TEXT,
                    company_name TEXT,
                    operator_name TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    report_path TEXT,
                    details_json TEXT,
                    created_by_user_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(client_id) REFERENCES clients(id),
                    FOREIGN KEY(created_by_user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id TEXT NOT NULL,
                    material_grade TEXT,
                    standard TEXT,
                    status TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_name TEXT,
                    user_email TEXT,
                    request_path TEXT,
                    details_json TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _hash_password(self, password: str) -> str:
        return hash_password(password)

    def log_audit_event(
        self,
        event_type: str,
        entity_name: Optional[str] = None,
        user_email: Optional[str] = None,
        request_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_logs (event_type, entity_name, user_email, request_path, details_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    entity_name,
                    user_email,
                    request_path,
                    json.dumps(details or {}, ensure_ascii=False),
                ),
            )
            return cursor.lastrowid

    def list_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            logs = []
            for row in rows:
                payload = dict(row)
                if payload.get("details_json"):
                    try:
                        payload["details"] = json.loads(payload["details_json"])
                    except json.JSONDecodeError:
                        payload["details"] = {}
                else:
                    payload["details"] = {}
                payload.pop("details_json", None)
                logs.append(payload)
            return logs

    def create_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = "operator",
        company_name: Optional[str] = None,
        is_active: bool = True,
    ) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (email, password_hash, full_name, role, company_name, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    email.strip().lower(),
                    self._hash_password(password),
                    full_name,
                    role,
                    company_name,
                    1 if is_active else 0,
                ),
            )
            return cursor.lastrowid

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email.strip().lower(),),
            ).fetchone()
            if row is None:
                return None
            return dict(row)

    def verify_password(self, email: str, password: str) -> bool:
        user = self.get_user_by_email(email)
        if not user:
            return False
        stored_hash = user["password_hash"]
        if stored_hash.startswith("pbkdf2_sha256$"):
            return verify_hash_password(password, stored_hash)
        return stored_hash == hashlib.sha256(password.strip().encode("utf-8")).hexdigest()

    def create_client(self, name: str, email: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO clients (name, email) VALUES (?, ?)",
                (name.strip(), email.strip() if email else None),
            )
            return cursor.lastrowid

    def list_clients(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM clients ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def save_report(
        self,
        client_id: int,
        sample_id: str,
        material_grade: Optional[str] = None,
        standard: Optional[str] = None,
        company_name: Optional[str] = None,
        operator_name: Optional[str] = None,
        status: str = "PENDING",
        report_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        created_by_user_id: Optional[int] = None,
    ) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reports (
                    client_id, sample_id, material_grade, standard, company_name,
                    operator_name, status, report_path, details_json, created_by_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    sample_id,
                    material_grade,
                    standard,
                    company_name,
                    operator_name,
                    status,
                    report_path,
                    json.dumps(details or {}, ensure_ascii=False),
                    created_by_user_id,
                ),
            )
            return cursor.lastrowid

    def list_reports(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT r.*, c.name as client_name
                FROM reports r
                LEFT JOIN clients c ON c.id = r.client_id
                ORDER BY r.created_at DESC
                """
            ).fetchall()
            reports = []
            for row in rows:
                payload = dict(row)
                if payload.get("details_json"):
                    try:
                        payload["details"] = json.loads(payload["details_json"])
                    except json.JSONDecodeError:
                        payload["details"] = {}
                else:
                    payload["details"] = {}
                payload.pop("details_json", None)
                reports.append(payload)
            return reports

    def save_test_run(self, record: Dict[str, Any], run_id: Optional[int] = None) -> int:
        config = record.get("config", {})
        with self.get_connection() as conn:
            values = (
                str(config.get("sample_id", "")),
                config.get("material_grade"),
                config.get("standard"),
                str(record.get("state", "STOPPED")),
                json.dumps(record, ensure_ascii=False, allow_nan=False),
            )
            if run_id is not None:
                cursor = conn.execute(
                    """
                    UPDATE test_runs
                    SET sample_id=?, material_grade=?, standard=?, status=?, record_json=?
                    WHERE id=?
                    """,
                    (*values, run_id),
                )
                if cursor.rowcount:
                    return run_id
            cursor = conn.execute(
                """
                INSERT INTO test_runs (sample_id, material_grade, standard, status, record_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                values,
            )
            return cursor.lastrowid

    def list_test_runs(self, search: str = "") -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, sample_id, material_grade, standard, status, created_at,
                       json_extract(record_json, '$.data_count') AS data_count
                FROM test_runs
                WHERE sample_id LIKE ? OR material_grade LIKE ?
                ORDER BY created_at DESC, id DESC
                """,
                (f"%{search}%", f"%{search}%"),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_test_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, created_at, record_json FROM test_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            record = json.loads(row["record_json"])
            record["run_id"] = row["id"]
            record["created_at"] = row["created_at"]
            return record

    def delete_test_run(self, run_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM test_runs WHERE id = ?", (run_id,))
            return cursor.rowcount > 0

    def list_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, email, full_name, role, company_name, is_active, created_at FROM users ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_total_counts(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
            reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
            audit_events = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
            return {"users": users, "clients": clients, "reports": reports, "audit_events": audit_events}


def ensure_seed_data(
    db: DatabaseManager,
    admin_email: Optional[str] = None,
    admin_password: Optional[str] = None,
) -> None:
    if bool(admin_email) != bool(admin_password):
        raise ValueError("Both bootstrap admin email and password must be configured")

    bootstrap_email = admin_email or os.getenv("UTM_BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_password = admin_password or os.getenv("UTM_BOOTSTRAP_ADMIN_PASSWORD")
    if bool(bootstrap_email) != bool(bootstrap_password):
        raise ValueError("Both bootstrap admin email and password must be configured")
    if bootstrap_email and bootstrap_password and not db.get_user_by_email(bootstrap_email):
        db.create_user(
            email=bootstrap_email,
            password=bootstrap_password,
            role="admin",
            is_active=True,
        )


if __name__ == "__main__":
    db = DatabaseManager()
    db.init_db()
    ensure_seed_data(db)
    print("Database initialized.")
