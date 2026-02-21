from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_log(log_file: Path, level: str, message: str, **fields: Any) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "level": level,
        "message": message,
    }
    if fields:
        payload.update(fields)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
