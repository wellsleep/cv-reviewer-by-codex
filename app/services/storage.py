import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict

from fastapi import HTTPException

from app.config import DB_FILE, UPLOAD_DIR


class JsonStorage:
    def __init__(self, db_file: Path) -> None:
        self.db_file = db_file
        self.lock = Lock()

    def exists(self) -> bool:
        return self.db_file.exists()

    def initialize(self, data):
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self._write(data)

    def load(self):
        with self.lock:
            if not self.db_file.exists():
                raise HTTPException(status_code=500, detail="storage not initialized")
            return json.loads(self.db_file.read_text(encoding="utf-8"))

    def save(self, data):
        with self.lock:
            self._write(data)

    def _write(self, data):
        self.db_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=self._json_default),
            encoding="utf-8",
        )

    @staticmethod
    def _json_default(value):
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def next_id(self, key: str) -> int:
        data = self.load()
        data["counters"][key] += 1
        next_value = data["counters"][key]
        self.save(data)
        return next_value

    def allocate_id(self, data, key):
        data["counters"][key] += 1
        return data["counters"][key]

    def get_job_rule(self):
        return self.load()["job_rule"]

    def set_job_rule(self, job_rule):
        data = self.load()
        job_rule["updatedAt"] = datetime.now().isoformat()
        data["job_rule"] = job_rule
        self.save(data)


storage = JsonStorage(DB_FILE)
