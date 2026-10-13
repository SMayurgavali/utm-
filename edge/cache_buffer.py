"""
Offline Ingestion Cache Buffer:
Resilience queue mechanism localizing data packets inside the edge computing cache
during localized network dropouts and automatically flushing backlogs once connections stabilize.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

class OfflineCacheBuffer:
    def __init__(self, db_path: str = "edge_offline_cache.db"):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id TEXT NOT NULL,
                    time_sec REAL NOT NULL,
                    force_n REAL NOT NULL,
                    displacement_mm REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

    def push(self, packet: Dict[str, Any]):
        """Append packet to local offline cache during network dropouts."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO telemetry_queue (sample_id, time_sec, force_n, displacement_mm)
                VALUES (?, ?, ?, ?)
            """, (
                packet.get("sample_id", "UNKNOWN"),
                float(packet.get("time_sec", 0.0)),
                float(packet.get("force_n", 0.0)),
                float(packet.get("displacement_mm", 0.0))
            ))
            conn.commit()
            conn.close()

    def push_batch(self, packets: List[Dict[str, Any]]):
        """Batch append packets."""
        if not packets:
            return
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            data = [
                (
                    p.get("sample_id", "UNKNOWN"),
                    float(p.get("time_sec", 0.0)),
                    float(p.get("force_n", 0.0)),
                    float(p.get("displacement_mm", 0.0))
                )
                for p in packets
            ]
            cursor.executemany("""
                INSERT INTO telemetry_queue (sample_id, time_sec, force_n, displacement_mm)
                VALUES (?, ?, ?, ?)
            """, data)
            conn.commit()
            conn.close()

    def peek(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch oldest pending packets without deleting."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, sample_id, time_sec, force_n, displacement_mm
                FROM telemetry_queue
                ORDER BY id ASC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "id": r[0],
                    "sample_id": r[1],
                    "time_sec": r[2],
                    "force_n": r[3],
                    "displacement_mm": r[4]
                }
                for r in rows
            ]

    def remove_ids(self, ids: List[int]):
        """Remove confirmed flushed packets."""
        if not ids:
            return
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in ids)
            cursor.execute(f"DELETE FROM telemetry_queue WHERE id IN ({placeholders})", ids)
            conn.commit()
            conn.close()

    def count(self) -> int:
        """Returns total count of pending cached frames."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM telemetry_queue")
            count = cursor.fetchone()[0]
            conn.close()
            return count

    def clear(self):
        """Clear the cache."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM telemetry_queue")
            conn.commit()
            conn.close()
