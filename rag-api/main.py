"""
main.py — RAG Chatbot API s Ollama + ML predikcija servisa + MongoDB servisna knjižica
"""

import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime as dt

import httpx
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from indexer import (
    index_pdf, search, delete_vehicle as qdrant_delete,
    load_registry, ensure_collection
)
from dispatch import create_dispatch, list_dispatches, update_dispatch_status
from service_book import (
    ensure_indexes, create_vehicle, list_vehicles,
    get_vehicle_by_vin, get_vehicle_by_plate,
    update_vehicle, delete_vehicle,
    add_service_entry, delete_service_entry,
)
from ml_model import (
    predict as ml_predict,
    get_metrics as ml_get_metrics,
    add_real_datapoint,
    train as ml_train,
)

app = FastAPI(title="Autoservis RAG API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_KEY    = os.environ.get("ADMIN_KEY", "admin123")
OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

HR_TO_EN = {
    "guma": "tire tyre flat puncture wheel",
    "pukla": "flat puncture burst",
    "puklo": "flat puncture burst",
    "rezervna": "spare tire wheel",
    "kotač": "wheel tire",
    "akumulator": "battery dead discharged",
    "baterija": "battery dead",
    "ne pali": "won't start dead battery",
    "ne upali": "won't start engine failure",
    "pregrijava": "overheating overheat temperature",
    "pregrijavanje": "overheating coolant temperature",
    "gorivo": "fuel gasoline diesel empty",
    "nestalo": "out of fuel empty",
    "osigurač": "fuse blown electrical",
    "pregorio": "blown fuse",
    "kočnice": "brakes brake failure",
    "kočnica": "brake",
    "motor": "engine",
    "ulje": "oil level",
    "lampica": "warning light indicator lamp",
    "upozorenje": "warning light",
    "mjenjač": "transmission gearbox",
    "upravljač": "steering wheel",
    "volan": "steering",
    "airbag": "airbag warning",
    "rashladna": "coolant temperature",
    "trokut": "warning triangle emergency",
    "tegljenje": "towing tow",
    "vuča": "towing",
    "jump": "jump start battery cables",
    "kablovi": "jump start cables battery",
}

def expand_query(query: str) -> str:
    q = query.lower()
    expansions = [en for hr, en in HR_TO_EN.items() if hr in q]
    return query + " " + " ".join(expansions) if expansions else query

SYSTEM_PROMPT = """You are a roadside assistant for {vehicle_info}. Always respond in {language}.

Use ONLY the manual excerpts below to answer. Do not invent information.

Manual excerpts:
---
{context}
---

Rules:
1. For simple problems (flat tire, dead battery, blown fuse, low fuel, warning light) — give clear numbered steps from the manual. Do NOT use [DISPATCH_NEEDED] for these.
2. For overheating — tell user to STOP immediately, turn off engine, wait 10 min, do NOT open coolant cap while hot. Do NOT use [DISPATCH_NEEDED] unless coolant is leaking or engine won't cool down.
3. ONLY use [DISPATCH_NEEDED] for truly dangerous problems: brake failure, fire smell, airbag warning light, complete steering loss, engine seizure, fuel leak. Ask for their phone number so a technician can contact them directly.
4. Always reference which page the information is from.
5. Keep answers short and practical."""


@app.on_event("startup")
def startup():
    try:
        ensure_collection()
        print("[startup] Qdrant kolekcija OK")
    except Exception as e:
        print(f"[startup] Qdrant greška: {e}")

    try:
        ensure_indexes()
        print("[startup] MongoDB indeksi OK")
    except Exception as e:
        print(f"[startup] MongoDB greška: {e}")

    try:
        ml_get_metrics()
        print("[startup] ML model OK")
    except Exception:
        print("[startup] ML model nije treniran — treniram...")
        try:
            ml_train()
            print("[startup] ML model treniran")
        except Exception as e:
            print(f"[startup] ML trening greška: {e}")


async def ollama_chat(messages: list[dict], system: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 600},
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Ollama timeout.")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Ollama greška: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Ollama nije dostupan: {str(e)}")


def require_service_auth(admin_key: str):
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Nevažeći ključ")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {"status": "ok", "service": "rag-api", "ollama": "ok" if ollama_ok else "nedostupan", "model": OLLAMA_MODEL}


# ── RAG Vehicles ──────────────────────────────────────────────────────────────

@app.get("/vehicles")
def list_rag_vehicles():
    return {"vehicles": list(load_registry().values())}


@app.post("/vehicles/upload")
async def upload_vehicle(
    file: UploadFile = File(...),
    make: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    language: str = Form("hr"),
    admin_key: str = Form(...),
):
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Nevažeći admin ključ")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Samo PDF datoteke")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        info = index_pdf(tmp_path, make, model, year, language)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return {"message": f"Priručnik za {make} {model} {year} indeksiran", "vehicle": info}


@app.delete("/vehicles/{key}")
def remove_rag_vehicle(key: str, admin_key: str):
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Nevažeći admin ključ")
    qdrant_delete(key)
    return {"message": f"Vozilo {key} obrisano"}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    vehicle_key: str
    messages: list[ChatMessage]
    location: str | None = None
    contact: str | None = None
    problem_summary: str | None = None
    language: str = "Croatian"


@app.post("/chat")
async def chat(req: ChatRequest):
    registry = load_registry()
    vehicle = registry.get(req.vehicle_key)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")

    user_messages = [m for m in req.messages if m.role == "user"]
    last_query = user_messages[-1].content if user_messages else ""
    expanded_query = expand_query(last_query)
    results = search(req.vehicle_key, expanded_query, top_k=6)
    context = "\n\n---\n\n".join(f"[Stranica {r['page']}]\n{r['text']}" for r in results) if results else "Nema relevantnih dijelova priručnika."

    vehicle_info = f"{vehicle['make']} {vehicle['model']} {vehicle['year']}"
    system = SYSTEM_PROMPT.format(vehicle_info=vehicle_info, context=context, language=req.language)
    ollama_messages = [{"role": m.role, "content": m.content} for m in req.messages]
    raw = await ollama_chat(ollama_messages, system)

    needs_dispatch = "[DISPATCH_NEEDED]" in raw
    location_from_reply = None
    if "[LOCATION:" in raw:
        try:
            loc_start = raw.index("[LOCATION:") + len("[LOCATION:")
            loc_end = raw.index("]", loc_start)
            location_from_reply = raw[loc_start:loc_end].strip()
        except ValueError:
            pass

    dispatch = None
    location = req.location or location_from_reply
    if location and needs_dispatch:
        dispatch = create_dispatch(
            vehicle_key=req.vehicle_key, vehicle_description=vehicle_info,
            problem=req.problem_summary or last_query, location=location, contact=req.contact,
        )

    clean = raw.replace("[DISPATCH_NEEDED]", "")
    if location_from_reply:
        clean = clean.replace(f"[LOCATION: {location_from_reply}]", "")
    clean = clean.strip()

    return {
        "reply": clean, "needs_dispatch": needs_dispatch,
        "dispatch_created": dispatch is not None,
        "dispatch_id": dispatch["id"] if dispatch else None,
        "sources": [{"page": r["page"], "score": r["score"]} for r in results],
    }


# ── Dispatches ────────────────────────────────────────────────────────────────

@app.get("/dispatches")
def get_dispatches(status: str | None = None, admin_key: str = ""):
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Nevažeći admin ključ")
    return {"dispatches": list_dispatches(status)}

class DispatchStatusUpdate(BaseModel):
    status: str
    admin_key: str

@app.put("/dispatches/{dispatch_id}/status")
def update_dispatch(dispatch_id: str, payload: DispatchStatusUpdate):
    if payload.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Nevažeći admin ključ")
    if payload.status not in {"pending", "assigned", "resolved"}:
        raise HTTPException(status_code=400, detail="Nevažeći status")
    updated = update_dispatch_status(dispatch_id, payload.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Dispatch nije pronađen")
    return updated


# ── Service Book modeli ───────────────────────────────────────────────────────

class VehicleInfo(BaseModel):
    make: str
    model: str
    year: int
    engine_cc: Optional[int] = None
    engine_kw: Optional[int] = None

class OwnerInfo(BaseModel):
    name: str
    phone: Optional[str] = ""
    email: Optional[str] = ""

class ServiceBookCreate(BaseModel):
    vin: str
    plate: str
    vehicle: VehicleInfo
    owner: OwnerInfo
    next_service_km: Optional[int] = None

class ServiceBookUpdate(BaseModel):
    vehicle: Optional[VehicleInfo] = None
    owner: Optional[OwnerInfo] = None
    plate: Optional[str] = None
    next_service_km: Optional[int] = None

class ServiceItems(BaseModel):
    oil_filter: Optional[bool] = None
    cabin_filter: Optional[bool] = None
    fuel_filter: Optional[bool] = None
    air_filter: Optional[bool] = None
    spark_plug: Optional[bool] = None
    toothed_belt: Optional[bool] = None
    micro_belt: Optional[bool] = None
    brake_fluid: Optional[bool] = None
    coolant: Optional[bool] = None
    gearbox_oil: Optional[bool] = None
    power_steering_fluid: Optional[bool] = None

class ServiceEntryCreate(BaseModel):
    date: str
    km: int
    oil_type: Optional[str] = ""
    items: ServiceItems = Field(default_factory=ServiceItems)
    extra: Optional[str] = ""

class ServiceEntryDelete(BaseModel):
    date: str
    km: int


# ── Service Book endpointi ────────────────────────────────────────────────────

@app.get("/service-book")
def sb_list(admin_key: str = ""):
    require_service_auth(admin_key)
    return {"vehicles": list_vehicles()}

@app.get("/service-book/{vin}")
def sb_get(vin: str, admin_key: str = ""):
    require_service_auth(admin_key)
    doc = get_vehicle_by_vin(vin)
    if not doc:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")
    return doc

@app.get("/service-book/plate/{plate}")
def sb_get_by_plate(plate: str, admin_key: str = ""):
    require_service_auth(admin_key)
    doc = get_vehicle_by_plate(plate)
    if not doc:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")
    return doc

@app.post("/service-book", status_code=201)
def sb_create(payload: ServiceBookCreate, admin_key: str = ""):
    require_service_auth(admin_key)
    try:
        doc = create_vehicle(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return doc

@app.put("/service-book/{vin}")
def sb_update(vin: str, payload: ServiceBookUpdate, admin_key: str = ""):
    require_service_auth(admin_key)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Nema podataka za ažuriranje")
    doc = update_vehicle(vin, updates)
    if not doc:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")
    return doc

@app.delete("/service-book/{vin}")
def sb_delete(vin: str, admin_key: str = ""):
    require_service_auth(admin_key)
    ok = delete_vehicle(vin)
    if not ok:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")
    return {"message": f"Vozilo {vin} obrisano"}

@app.post("/service-book/{vin}/entries")
def sb_add_entry(vin: str, payload: ServiceEntryCreate, admin_key: str = "", recorded_by: str = "unknown"):
    require_service_auth(admin_key)

    vehicle = get_vehicle_by_vin(vin)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")

    history = vehicle.get("service_history", [])

    # Auto ML fine-tune — izračunaj stvarni interval iz prethodnog zapisa
    if len(history) >= 1:
        prev = history[-1]
        actual_interval = payload.km - prev["km"]
        if actual_interval > 1000:
            v = vehicle["vehicle"]
            try:
                prev_date = dt.strptime(prev["date"], "%Y-%m-%d")
                curr_date = dt.strptime(payload.date, "%Y-%m-%d")
                days = (curr_date - prev_date).days
                avg_daily = actual_interval / days if days > 0 else 40.0
            except Exception:
                avg_daily = 40.0

            try:
                n_real = add_real_datapoint(
                    brand=v["make"],
                    avg_daily_km=round(avg_daily, 1),
                    year=v["year"],
                    engine_cc=v.get("engine_cc") or 1600,
                    engine_kw=v.get("engine_kw") or 85,
                    total_km_at_service=payload.km,
                    num_prev_services=len(history),
                    actual_km_interval=actual_interval,
                )
                print(f"[ml] Real datapoint added. Total: {n_real}")
            except Exception as e:
                print(f"[ml] Fine-tune greška: {e}")

    doc = add_service_entry(vin, payload.model_dump(), recorded_by)
    if not doc:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")
    return doc

@app.delete("/service-book/{vin}/entries")
def sb_delete_entry(vin: str, payload: ServiceEntryDelete, admin_key: str = ""):
    require_service_auth(admin_key)
    doc = delete_service_entry(vin, payload.date, payload.km)
    if not doc:
        raise HTTPException(status_code=404, detail="Vozilo ili zapis nije pronađen")
    return doc


# ── ML Predikcija ─────────────────────────────────────────────────────────────

class MLPredictRequest(BaseModel):
    brand: str
    year: int
    engine_cc: int
    engine_kw: int
    total_km: int
    avg_daily_km: float
    num_prev_services: int = 0
    month: int | None = None


@app.post("/ml/predict")
def ml_predict_endpoint(payload: MLPredictRequest, admin_key: str = ""):
    require_service_auth(admin_key)
    return ml_predict(
        brand=payload.brand,
        avg_daily_km=payload.avg_daily_km,
        year=payload.year,
        engine_cc=payload.engine_cc,
        engine_kw=payload.engine_kw,
        total_km=payload.total_km,
        num_prev_services=payload.num_prev_services,
        month=payload.month,
    )


@app.post("/ml/predict/{vin}")
def ml_predict_for_vehicle(vin: str, current_km: int, avg_daily_km: float, admin_key: str = ""):
    require_service_auth(admin_key)
    vehicle = get_vehicle_by_vin(vin)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")
    v = vehicle["vehicle"]
    history = vehicle.get("service_history", [])
    result = ml_predict(
        brand=v["make"],
        avg_daily_km=avg_daily_km,
        year=v["year"],
        engine_cc=v.get("engine_cc") or 1600,
        engine_kw=v.get("engine_kw") or 85,
        total_km=current_km,
        num_prev_services=len(history),
    )
    result["vin"] = vin
    result["vehicle"] = f"{v['make']} {v['model']} {v['year']}"
    return result


@app.get("/ml/metrics")
def ml_metrics_endpoint(admin_key: str = ""):
    require_service_auth(admin_key)
    return ml_get_metrics()


@app.post("/ml/retrain")
def ml_retrain_endpoint(admin_key: str = ""):
    require_service_auth(admin_key)
    metrics = ml_train()
    return {"message": "Model uspješno retreniran", "metrics": metrics}