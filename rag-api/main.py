"""
main.py — RAG Chatbot API s Ollama (lokalni LLM, bez eksternih API-ja)
"""

import os
import shutil
import tempfile
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from indexer import (
    index_pdf, search, delete_vehicle as qdrant_delete,
    load_registry, ensure_collection
)
from dispatch import create_dispatch, list_dispatches, update_dispatch_status

app = FastAPI(title="Autoservis RAG API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_KEY    = os.environ.get("ADMIN_KEY", "admin123")
OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

# HR → EN rječnik za query expansion
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
    expansions = []
    for hr, en in HR_TO_EN.items():
        if hr in q:
            expansions.append(en)
    if expansions:
        return query + " " + " ".join(expansions)
    return query


SYSTEM_PROMPT = """You are a roadside assistant for {vehicle_info}. Always respond in {language}.

Use ONLY the manual excerpts below to answer. Do not invent information.

Manual excerpts:
---
{context}
---

Rules:
1. For simple problems (flat tire, dead battery, blown fuse, low fuel, warning light) — give clear numbered steps from the manual. Do NOT use [DISPATCH_NEEDED] for these.
2. For overheating — tell user to STOP immediately, turn off engine, wait 10 min, do NOT open coolant cap while hot. Do NOT use [DISPATCH_NEEDED] unless coolant is leaking or engine won't cool down.
3. ONLY use [DISPATCH_NEEDED] for truly dangerous problems: brake failure, fire smell, airbag warning light, complete steering loss, engine seizure, fuel leak.
4. Always reference which page the information is from.
5. Keep answers short and practical."""


@app.on_event("startup")
def startup():
    try:
        ensure_collection()
        print("[startup] Qdrant kolekcija OK")
    except Exception as e:
        print(f"[startup] Qdrant greška: {e}")


async def ollama_chat(messages: list[dict], system: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 600,
        }
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Ollama timeout — model se možda još učitava.")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Ollama greška: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Ollama nije dostupan: {str(e)}")


@app.get("/health")
async def health():
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "status": "ok",
        "service": "rag-api",
        "ollama": "ok" if ollama_ok else "nedostupan",
        "model": OLLAMA_MODEL,
    }


@app.get("/vehicles")
def list_vehicles():
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

    return {
        "message": f"Priručnik za {make} {model} {year} indeksiran",
        "vehicle": info,
    }


@app.delete("/vehicles/{key}")
def remove_vehicle(key: str, admin_key: str):
    if admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Nevažeći admin ključ")
    qdrant_delete(key)
    return {"message": f"Vozilo {key} obrisano"}


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    vehicle_key: str
    messages: list[ChatMessage]
    location: str | None = None
    contact: str | None = None
    problem_summary: str | None = None
    language: str = "Croatian"  # Croatian ili English


@app.post("/chat")
async def chat(req: ChatRequest):
    registry = load_registry()
    vehicle = registry.get(req.vehicle_key)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")

    user_messages = [m for m in req.messages if m.role == "user"]
    last_query = user_messages[-1].content if user_messages else ""

    expanded_query = expand_query(last_query)
    print(f"[chat] Lang: {req.language} | Query: '{last_query}' → '{expanded_query}'")

    results = search(req.vehicle_key, expanded_query, top_k=6)
    context = "\n\n---\n\n".join(
        f"[Stranica {r['page']}]\n{r['text']}" for r in results
    ) if results else "Nema relevantnih dijelova priručnika."

    vehicle_info = f"{vehicle['make']} {vehicle['model']} {vehicle['year']}"
    system = SYSTEM_PROMPT.format(
        vehicle_info=vehicle_info,
        context=context,
        language=req.language,
    )

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
            vehicle_key=req.vehicle_key,
            vehicle_description=vehicle_info,
            problem=req.problem_summary or last_query,
            location=location,
            contact=req.contact,
        )

    clean = raw.replace("[DISPATCH_NEEDED]", "")
    if location_from_reply:
        clean = clean.replace(f"[LOCATION: {location_from_reply}]", "")
    clean = clean.strip()

    return {
        "reply": clean,
        "needs_dispatch": needs_dispatch,
        "dispatch_created": dispatch is not None,
        "dispatch_id": dispatch["id"] if dispatch else None,
        "sources": [{"page": r["page"], "score": r["score"]} for r in results],
    }


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