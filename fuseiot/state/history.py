from typing import List, Dict, Any
from datetime import datetime
import sqlite3
import json

from ..config import CONFIG  # Assuming global config with db_path

class StateHistory:
    """Manages historical state data using SQLite."""

    def __init__(self, db_path: str = CONFIG.get("state_db", "state_history.db")):
        self._conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self) -> None:
        """Create history table if not exists."""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                timestamp DATETIME,
                state TEXT
            )
        """)
        self._conn.commit()

    def log_state(self, device_id: str, state: Dict[str, Any]) -> None:
        """Log a state change."""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO history (device_id, timestamp, state)
            VALUES (?, ?, ?)
        """, (device_id, datetime.now().isoformat(), json.dumps(state)))
        self._conn.commit()

    def get_history(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve history for a device."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT timestamp, state FROM history
            WHERE device_id = ? ORDER BY timestamp DESC LIMIT ?
        """, (device_id, limit))
        return [{"timestamp": ts, "state": json.loads(st)} for ts, st in cursor.fetchall()]

    def close(self) -> None:
        """Close database connection."""
        self._conn.close()