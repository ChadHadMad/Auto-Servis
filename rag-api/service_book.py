"""
service_book.py — Digitalna servisna knjižica u MongoDB-u.

Kolekcija: service_books
Jedan dokument = jedno vozilo s kompletnom servisnom poviješću.
"""

import os
from datetime import datetime
from typing import Optional
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongodb:27017")
MONGO_DB  = os.environ.get("MONGO_DB",  "autoservis")
COLLECTION = "service_books"

SERVICE_INTERVAL_KM = 15000


def _get_col():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    return client[MONGO_DB][COLLECTION]


def ensure_indexes():
    col = _get_col()
    col.create_index("vin",   unique=True)
    col.create_index("plate", unique=True)
    print("[service_book] MongoDB indexes OK")


# ── Vehicles ─────────────────────────────────────────────────────────────────

def create_vehicle(data: dict) -> dict:
    """
    Kreira novi dokument servisne knjižice.
    data mora sadržavati: vin, plate, vehicle, owner
    """
    col = _get_col()

    doc = {
        "vin":   data["vin"].upper().strip(),
        "plate": data["plate"].upper().strip(),
        "vehicle": {
            "make":       data["vehicle"]["make"],
            "model":      data["vehicle"]["model"],
            "year":       data["vehicle"]["year"],
            "engine_cc":  data["vehicle"].get("engine_cc"),
            "engine_kw":  data["vehicle"].get("engine_kw"),
        },
        "owner": {
            "name":  data["owner"].get("name", ""),
            "phone": data["owner"].get("phone", ""),
            "email": data["owner"].get("email", ""),
        },
        "next_service_km": data.get("next_service_km"),
        "service_history": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    try:
        col.insert_one(doc)
    except DuplicateKeyError as e:
        raise ValueError(f"Vozilo s tim VIN-om ili tablicom već postoji: {e}")

    doc.pop("_id", None)
    return doc


def list_vehicles() -> list:
    col = _get_col()
    docs = list(col.find({}, {"_id": 0}).sort("created_at", DESCENDING))
    return docs


def get_vehicle_by_vin(vin: str) -> Optional[dict]:
    col = _get_col()
    doc = col.find_one({"vin": vin.upper().strip()}, {"_id": 0})
    return doc


def get_vehicle_by_plate(plate: str) -> Optional[dict]:
    col = _get_col()
    doc = col.find_one({"plate": plate.upper().strip()}, {"_id": 0})
    return doc


def update_vehicle(vin: str, updates: dict) -> Optional[dict]:
    """Ažurira podatke o vozilu (ne servisnu povijest)."""
    col = _get_col()
    allowed = {"vehicle", "owner", "plate", "next_service_km"}
    safe = {k: v for k, v in updates.items() if k in allowed}
    safe["updated_at"] = datetime.utcnow().isoformat()

    result = col.find_one_and_update(
        {"vin": vin.upper()},
        {"$set": safe},
        return_document=True,
        projection={"_id": 0},
    )
    return result


def delete_vehicle(vin: str) -> bool:
    col = _get_col()
    result = col.delete_one({"vin": vin.upper().strip()})
    return result.deleted_count > 0


# ── Service entries ───────────────────────────────────────────────────────────

def add_service_entry(vin: str, entry: dict, recorded_by: str) -> Optional[dict]:
    """
    Dodaje novi servisni zapis vozilu.
    Automatski izračunava next_service_km = km + 15000.
    """
    col = _get_col()

    km = entry["km"]
    next_km = km + SERVICE_INTERVAL_KM

    record = {
        "date":        entry["date"],
        "km":          km,
        "oil_type":    entry.get("oil_type", ""),
        "recorded_by": recorded_by,
        "items": {
            "oil_filter":            entry["items"].get("oil_filter"),
            "cabin_filter":          entry["items"].get("cabin_filter"),
            "fuel_filter":           entry["items"].get("fuel_filter"),
            "air_filter":            entry["items"].get("air_filter"),
            "spark_plug":            entry["items"].get("spark_plug"),
            "toothed_belt":          entry["items"].get("toothed_belt"),
            "micro_belt":            entry["items"].get("micro_belt"),
            "brake_fluid":           entry["items"].get("brake_fluid"),
            "coolant":               entry["items"].get("coolant"),
            "gearbox_oil":           entry["items"].get("gearbox_oil"),
            "power_steering_fluid":  entry["items"].get("power_steering_fluid"),
        },
        "extra":            entry.get("extra", ""),
        "next_service_km":  next_km,
        "created_at":       datetime.utcnow().isoformat(),
    }

    result = col.find_one_and_update(
        {"vin": vin.upper()},
        {
            "$push": {"service_history": record},
            "$set":  {
                "next_service_km": next_km,
                "updated_at": datetime.utcnow().isoformat(),
            },
        },
        return_document=True,
        projection={"_id": 0},
    )
    return result


def delete_service_entry(vin: str, entry_date: str, entry_km: int) -> Optional[dict]:
    """Briše servisni zapis prema datumu i km."""
    col = _get_col()
    result = col.find_one_and_update(
        {"vin": vin.upper()},
        {"$pull": {"service_history": {"date": entry_date, "km": entry_km}}},
        return_document=True,
        projection={"_id": 0},
    )
    return result
