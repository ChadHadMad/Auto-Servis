"""
indexer.py — PDF → chunks → embeddings → Qdrant
Koristi fastembed direktno za generiranje vektora.
"""

import re
import json
import uuid
from pathlib import Path
from pypdf import PdfReader
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)

QDRANT_URL   = "http://qdrant:6333"
COLLECTION   = "manuals"
EMBED_MODEL  = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE  = 384

REGISTRY_FILE = Path("/app/data/vehicles.json")
REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection():
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"[indexer] Kolekcija '{COLLECTION}' kreirana.")
    client.close()


def clean_text(text: str) -> str:
    text = re.sub(r'\b([A-Z])\s([a-z])', r'\1\2', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_chunks(pdf_path: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    reader = PdfReader(pdf_path)
    chunks = []
    for i, page in enumerate(reader.pages):
        raw = page.extract_text()
        if not raw:
            continue
        text = clean_text(raw)
        if len(text) < 60:
            continue
        if len(text) > chunk_size:
            for start in range(0, len(text), chunk_size - overlap):
                part = text[start:start + chunk_size]
                if len(part) > 60:
                    chunks.append({"page": i + 1, "text": part})
        else:
            chunks.append({"page": i + 1, "text": text})
    return chunks


def index_pdf(pdf_path: str, make: str, model: str, year: int, language: str = "hr") -> dict:
    ensure_collection()

    vehicle_key = f"{make.lower()}_{model.lower().replace(' ', '_')}_{year}"
    chunks = extract_chunks(pdf_path)

    if not chunks:
        raise ValueError("PDF ne sadrži ekstraktabilan tekst.")

    print(f"[indexer] {len(chunks)} chunkova, generiranje vektora...")

    # FastEmbed direktno
    embed_model = TextEmbedding(EMBED_MODEL)
    texts = [c["text"] for c in chunks]
    vectors = list(embed_model.embed(texts))

    print(f"[indexer] Vektori generirani, upisivanje u Qdrant...")

    client = get_client()

    # Izbriši stare podatke za ovo vozilo
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="vehicle_key", match=MatchValue(value=vehicle_key))]
        ),
    )

    # Batch upsert po 100
    points = []
    for chunk, vector in zip(chunks, vectors):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vector.tolist(),
            payload={
                "vehicle_key": vehicle_key,
                "make": make,
                "model": model,
                "year": year,
                "language": language,
                "page": chunk["page"],
                "text": chunk["text"],
            }
        ))

    for i in range(0, len(points), 100):
        client.upsert(collection_name=COLLECTION, points=points[i:i+100])

    client.close()
    print(f"[indexer] {len(points)} vektora upisano u Qdrant.")

    info = {
        "key": vehicle_key,
        "make": make,
        "model": model,
        "year": year,
        "language": language,
        "total_chunks": len(chunks),
    }
    _update_registry(vehicle_key, info)
    return info


def search(vehicle_key: str, query: str, top_k: int = 6) -> list[dict]:
    """Semantička pretraga — embed query pa traži u Qdrantu."""
    embed_model = TextEmbedding(EMBED_MODEL)
    query_vector = list(embed_model.embed([query]))[0].tolist()

    client = get_client()
    results = client.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="vehicle_key", match=MatchValue(value=vehicle_key))]
        ),
        limit=top_k,
    )
    client.close()

    return [
        {
            "page": r.payload.get("page"),
            "text": r.payload.get("text", ""),
            "score": round(r.score, 3),
        }
        for r in results
    ]


def delete_vehicle(vehicle_key: str) -> bool:
    client = get_client()
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="vehicle_key", match=MatchValue(value=vehicle_key))]
        ),
    )
    client.close()
    _remove_from_registry(vehicle_key)
    return True


def load_registry() -> dict:
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text())
    return {}


def _update_registry(key: str, info: dict):
    reg = load_registry()
    reg[key] = info
    REGISTRY_FILE.write_text(json.dumps(reg, ensure_ascii=False, indent=2))


def _remove_from_registry(key: str):
    reg = load_registry()
    reg.pop(key, None)
    REGISTRY_FILE.write_text(json.dumps(reg, ensure_ascii=False, indent=2))