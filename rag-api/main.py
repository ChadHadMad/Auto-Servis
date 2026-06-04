"""
main.py — RAG Chatbot API s Ollama (lokalni LLM, bez eksternih API-ja)

Endpointi:
  GET  /health
  GET  /vehicles
  POST /vehicles/upload
  DELETE /vehicles/{key}
  POST /chat
  GET  /dispatches
  PUT  /dispatches/{id}/status
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

ADMIN_KEY   = os.environ.get("ADMIN_KEY", "admin123")
OLLAMA_URL  = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = """Ti si AI asistent za korisnike automehaničarskog servisa i vozače koji su ostali na cesti.

Vozilo korisnika: {vehicle_info}

Tvoje dvije uloge:
1. Pomoć na cesti — dijagnoza problema i upute iz priručnika vozila
2. Zakazivanje servisa — informacije o terminima i uslugama

Kada možeš sam pomoći (jednostavni problemi):
- Pukla guma, prazan akumulator, nestalo goriva, pregorio osigurač, upozoravajuća lampica
- Daj jasne upute korak-po-korak iz priručnika

Kada trebaš poslati tehničara [DISPATCH_NEEDED]:
- Ozbiljni kvarovi (motor, kočnice, mjenjač, airbag lampica)
- Korisnik ne može sam sigurno popraviti

Tijek za dispatch:
1. Objasni situaciju i uključi [DISPATCH_NEEDED] u odgovor
2. Pitaj za lokaciju i kontakt
3. Kada dobiješ lokaciju — uključi [LOCATION: <lokacija>] u odgovor
4. Potvrdi da je tehničar upućen

Relevantni dijelovi priručnika:
---
{context}
---

Budi konkretan i jasan. Upute piši kao numerirane korake.
Odgovaraj na jeziku korisnika."""


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    try:
        ensure_collection()
        print("[startup] Qdrant kolekcija OK")
    except Exception as e:
        print(f"[startup] Qdrant greška: {e}")


# ── Ollama helper ─────────────────────────────────────────────────────────────

async def ollama_chat(messages: list[dict], system: str) -> str:
    """
    Pozovi Ollama /api/chat endpoint.
    messages format: [{"role": "user"|"assistant", "content": "..."}]
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 800,
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


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    # Provjeri Ollama
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


# ── Vozila ─────────────────────────────────────────────────────────────────────

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


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    vehicle_key: str
    messages: list[ChatMessage]
    location: str | None = None
    contact: str | None = None
    problem_summary: str | None = None


@app.post("/chat")
async def chat(req: ChatRequest):
    registry = load_registry()
    vehicle = registry.get(req.vehicle_key)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vozilo nije pronađeno")

    # RAG — semantička pretraga Qdrant
    user_messages = [m for m in req.messages if m.role == "user"]
    last_query = user_messages[-1].content if user_messages else ""

    results = search(req.vehicle_key, last_query, top_k=6)
    context = "\n\n---\n\n".join(
        f"[Stranica {r['page']}]\n{r['text']}" for r in results
    ) if results else "Nema relevantnih dijelova priručnika."

    vehicle_info = f"{vehicle['make']} {vehicle['model']} {vehicle['year']}"
    system = SYSTEM_PROMPT.format(vehicle_info=vehicle_info, context=context)

    # Pozovi Ollama
    ollama_messages = [{"role": m.role, "content": m.content} for m in req.messages]
    raw = await ollama_chat(ollama_messages, system)

    needs_dispatch = "[DISPATCH_NEEDED]" in raw

    # Parsaj lokaciju iz odgovora
    location_from_reply = None
    if "[LOCATION:" in raw:
        try:
            loc_start = raw.index("[LOCATION:") + len("[LOCATION:")
            loc_end = raw.index("]", loc_start)
            location_from_reply = raw[loc_start:loc_end].strip()
        except ValueError:
            pass

    # Kreiraj dispatch ako imamo lokaciju
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

    # Očisti markere iz odgovora
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