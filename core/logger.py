"""Structured JSON Lines logger for recording agent interactions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunLogger:
    """Writes and reads per-run agent interaction logs in JSON Lines format."""

    def __init__(self, run_id: str, base_dir: str | Path = "runs") -> None:
        """Initialize the logger for a specific run_id under base_dir."""
        if not run_id or not run_id.strip():
            raise ValueError("run_id must be a non-empty string.")
        self.run_id: str = run_id
        self.base_dir: Path = Path(base_dir)
        self.run_dir: Path = self.base_dir / self.run_id
        self.log_file: Path = self.run_dir / "log.jsonl"

    def log_interaction(
        self,
        agent_name: str,
        input_summary: str,
        prompt: str | None = None,
        raw_output: str | None = None,
        duration: float = 0.0,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Append a single agent interaction record as a JSON line."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        entry: dict[str, Any] = {
            "agent_name": agent_name,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "input_summary": input_summary,
            "prompt": prompt,
            "raw_output": raw_output,
            "duration": float(duration),
        }
        with self.log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    # Alias for convenience
    log = log_interaction

    def read_log(self) -> list[dict[str, Any]]:
        """Read back all logged agent interactions from the JSONL file."""
        if not self.log_file.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.log_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    entries.append(json.loads(stripped))
        return entries

    # Alias for convenience
    read_logs = read_log
