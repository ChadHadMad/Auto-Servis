"""
dispatch.py — Pohrana zahtjeva za slanje tehničara.

Sprema u JSON datoteku (jednostavno, bez potrebe za extra bazom).
U produkciji: zamijeniti s direktnim pozivom na autoservis PostgreSQL.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

DISPATCH_FILE = Path("/app/data/dispatches.json")
DISPATCH_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load() -> list:
    if DISPATCH_FILE.exists():
        return json.loads(DISPATCH_FILE.read_text())
    return []


def _save(data: list):
    DISPATCH_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def create_dispatch(
    vehicle_key: str,
    vehicle_description: str,
    problem: str,
    location: str,
    contact: str | None = None,
) -> dict:
    """Spremi novi dispatch zahtjev."""
    record = {
        "id": str(uuid.uuid4()),
        "vehicle_key": vehicle_key,
        "vehicle_description": vehicle_description,
        "problem": problem,
        "location": location,
        "contact": contact,
        "status": "pending",       # pending | assigned | resolved
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    data = _load()
    data.append(record)
    _save(data)
    return record


def list_dispatches(status: str | None = None) -> list:
    """Dohvati sve dispatch zahtjeve, opcionalno filtrirano po statusu."""
    data = _load()
    if status:
        return [d for d in data if d["status"] == status]
    return sorted(data, key=lambda x: x["created_at"], reverse=True)


def update_dispatch_status(dispatch_id: str, new_status: str) -> dict | None:
    """Ažuriraj status dispatcha (pending → assigned → resolved)."""
    data = _load()
    for d in data:
        if d["id"] == dispatch_id:
            d["status"] = new_status
            d["updated_at"] = datetime.utcnow().isoformat()
            _save(data)
            return d
    return None
