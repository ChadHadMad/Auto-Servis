"""
ml_model.py — ML model za predikciju km do sljedećeg servisa.

Arhitektura:
  1. Pretreniran na sintetičkom datasetu (6000+ zapisa)
  2. Fine-tune na stvarnim podacima kad ih skupiš (online/batch)
  3. GradientBoostingRegressor — interpretabilan, robustan na mali dataset

Koristi se zajedno s predictor.py:
  - predictor.py → statistička predikcija (fallback za 0-2 zapisa)
  - ml_model.py  → ML predikcija (primarni model za 3+ zapisa)
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OrdinalEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from data_generator import generate_dataset

MODEL_PATH   = Path("/app/data/service_model.joblib")
METRICS_PATH = Path("/app/data/model_metrics.json")
REAL_DATA_PATH = Path("/app/data/real_training_data.csv")

# Features koje model koristi
CATEGORICAL_FEATURES = ["fuel_type", "brand_category"]
NUMERICAL_FEATURES   = [
    "vehicle_age", "engine_cc", "engine_kw",
    "total_km", "avg_daily_km", "month", "num_prev_services",
]
ALL_FEATURES = CATEGORICAL_FEATURES + NUMERICAL_FEATURES
TARGET = "km_to_next_service"

FUEL_TYPES      = ["petrol", "diesel", "hybrid", "lpg", "electric"]
BRAND_CATS      = ["economy", "mid", "premium"]
BRAND_CATEGORY_MAP = {
    "volkswagen": "mid",   "vw": "mid",
    "bmw": "premium",      "mercedes": "premium",  "audi": "premium",
    "volvo": "premium",    "lexus": "premium",
    "skoda": "economy",    "ford": "economy",       "opel": "economy",
    "peugeot": "economy",  "renault": "economy",    "fiat": "economy",
    "seat": "economy",     "dacia": "economy",      "hyundai": "economy",
    "kia": "economy",
    "toyota": "mid",       "honda": "mid",          "mazda": "mid",
    "nissan": "mid",       "subaru": "mid",
}


def _brand_to_category(brand: str) -> str:
    return BRAND_CATEGORY_MAP.get(brand.lower().strip(), "mid")


def _build_pipeline() -> Pipeline:
    """Konstruiraj sklearn pipeline s preprocessingom i modelom."""
    cat_transformer = OrdinalEncoder(
        categories=[FUEL_TYPES, BRAND_CATS],
        handle_unknown="use_encoded_value",
        unknown_value=-1,
    )
    preprocessor = ColumnTransformer([
        ("cat", cat_transformer, CATEGORICAL_FEATURES),
        ("num", StandardScaler(),  NUMERICAL_FEATURES),
    ])
    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.08,
        min_samples_leaf=10,
        subsample=0.8,
        random_state=42,
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])


# ── Trening ──────────────────────────────────────────────────────────────────

def train(n_synthetic: int = 6000, real_data_weight: float = 5.0) -> dict:
    """
    Treniraj model na sintetičkim + stvarnim podacima.
    
    real_data_weight: koliko puta dupliciramo stvarne podatke
                      da nadjačaju sintetičke (transfer learning)
    """
    print("[ml_model] Generiranje sintetičkog dataseta...")
    df_synth = generate_dataset(n_synthetic)

    # Dodaj brand_category ako nedostaje
    if "brand_category" not in df_synth.columns:
        df_synth["brand_category"] = df_synth["brand"].apply(_brand_to_category)

    frames = [df_synth]

    # Dodaj stvarne podatke s većom težinom (dupliciraj ih)
    if REAL_DATA_PATH.exists():
        df_real = pd.read_csv(REAL_DATA_PATH)
        if len(df_real) > 0:
            print(f"[ml_model] Stvarni podaci: {len(df_real)} zapisa (težina x{real_data_weight:.0f})")
            weight = max(1, int(real_data_weight))
            frames.extend([df_real] * weight)
        else:
            print("[ml_model] Nema stvarnih podataka — samo sintetički.")
    else:
        print("[ml_model] Nema stvarnih podataka — samo sintetički.")

    df = pd.concat(frames, ignore_index=True)
    df = df[ALL_FEATURES + [TARGET]].dropna()

    X = df[ALL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

    print(f"[ml_model] Trening: {len(X_train)} | Test: {len(X_test)} zapisa")
    print("[ml_model] Treniranje modela...")

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)

    # Evaluacija
    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)

    print(f"[ml_model] MAE: {mae:.0f} km | R²: {r2:.3f}")

    # Feature importance
    feat_importance = dict(zip(
        ALL_FEATURES,
        pipeline.named_steps["model"].feature_importances_.tolist()
    ))
    sorted_fi = dict(sorted(feat_importance.items(), key=lambda x: x[1], reverse=True))
    print(f"[ml_model] Top features: {list(sorted_fi.keys())[:4]}")

    # Spremi model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    metrics = {
        "trained_at": datetime.utcnow().isoformat(),
        "n_synthetic": n_synthetic,
        "n_real": len(df_real) if REAL_DATA_PATH.exists() and len(pd.read_csv(REAL_DATA_PATH)) > 0 else 0,
        "n_total": len(df),
        "mae_km": round(mae, 0),
        "r2": round(r2, 3),
        "feature_importance": {k: round(v, 4) for k, v in sorted_fi.items()},
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    print(f"[ml_model] Model spreman: {MODEL_PATH}")

    return metrics


def load_model():
    """Učitaj model iz diska. Trenira ga ako ne postoji."""
    if not MODEL_PATH.exists():
        print("[ml_model] Model ne postoji — treniram...")
        train()
    return joblib.load(MODEL_PATH)


# ── Predikcija ────────────────────────────────────────────────────────────────

def predict(
    brand: str,
    fuel_type: str,
    year: int,
    engine_cc: int,
    engine_kw: int,
    total_km: int,
    avg_daily_km: float,
    num_prev_services: int = 0,
    month: int = None,
) -> dict:
    """
    Predvidi km do sljedećeg servisa za jedno vozilo.
    
    Returns:
        dict s predikcijom i interpretacijom
    """
    if month is None:
        month = datetime.now().month

    pipeline = load_model()
    brand_cat = _brand_to_category(brand)
    vehicle_age = datetime.now().year - year

    # Normaliziraj fuel_type
    fuel_norm = fuel_type.lower().strip()
    if fuel_norm not in FUEL_TYPES:
        fuel_norm = "petrol"

    row = pd.DataFrame([{
        "fuel_type":          fuel_norm,
        "brand_category":     brand_cat,
        "vehicle_age":        vehicle_age,
        "engine_cc":          engine_cc,
        "engine_kw":          engine_kw,
        "total_km":           total_km,
        "avg_daily_km":       avg_daily_km,
        "month":              month,
        "num_prev_services":  num_prev_services,
    }])

    predicted_km = int(pipeline.predict(row)[0])
    # Zaokruži na 500 km
    predicted_km = round(predicted_km / 500) * 500
    predicted_km = max(5000, min(40000, predicted_km))

    # Predviđeni datum
    days_until = None
    predicted_date = None
    if avg_daily_km > 0:
        days_until = int(predicted_km / avg_daily_km)
        from datetime import date, timedelta
        predicted_date = (date.today() + timedelta(days=days_until)).isoformat()

    # Učitaj metrike za confidence
    metrics = {}
    if METRICS_PATH.exists():
        metrics = json.loads(METRICS_PATH.read_text())

    return {
        "predicted_km_interval": predicted_km,
        "predicted_date":        predicted_date,
        "days_until_service":    days_until,
        "model_mae_km":          metrics.get("mae_km"),
        "model_r2":              metrics.get("r2"),
        "input_features": {
            "brand":            brand,
            "brand_category":   brand_cat,
            "fuel_type":        fuel_norm,
            "vehicle_age":      vehicle_age,
            "engine_cc":        engine_cc,
            "engine_kw":        engine_kw,
            "total_km":         total_km,
            "avg_daily_km":     avg_daily_km,
        },
    }


# ── Fine-tuning s stvarnim podacima ──────────────────────────────────────────

def add_real_datapoint(
    brand: str,
    fuel_type: str,
    year: int,
    engine_cc: int,
    engine_kw: int,
    total_km_at_service: int,
    avg_daily_km: float,
    num_prev_services: int,
    actual_km_interval: int,
    month: int = None,
):
    """
    Dodaj stvarni servisni interval u training dataset.
    
    Poziva se automatski kad se unese novi servisni zapis u servisnu knjižicu.
    Model se retrenira svaki put kad ima 10+ novih stvarnih zapisa.
    """
    if month is None:
        month = datetime.now().month

    brand_cat = _brand_to_category(brand)
    vehicle_age = datetime.now().year - year

    row = {
        "fuel_type":             fuel_type.lower(),
        "brand_category":        brand_cat,
        "vehicle_age":           vehicle_age,
        "engine_cc":             engine_cc,
        "engine_kw":             engine_kw,
        "total_km":              total_km_at_service,
        "avg_daily_km":          avg_daily_km,
        "month":                 month,
        "num_prev_services":     num_prev_services,
        "km_to_next_service":    actual_km_interval,
        "added_at":              datetime.utcnow().isoformat(),
    }

    # Dodaj u CSV
    REAL_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_new = pd.DataFrame([row])

    if REAL_DATA_PATH.exists():
        df_existing = pd.read_csv(REAL_DATA_PATH)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(REAL_DATA_PATH, index=False)
    n_real = len(df_combined)
    print(f"[ml_model] Stvarni podatak dodan. Ukupno: {n_real} zapisa.")

    # Auto-retreniranje svaki put kad skupiš 10 novih zapisa
    if n_real % 10 == 0:
        print(f"[ml_model] Auto-retrening na {n_real} stvarnih zapisa...")
        train()

    return n_real


def get_metrics() -> dict:
    """Vrati metrike trenutnog modela."""
    if not METRICS_PATH.exists():
        return {"status": "model nije treniran"}
    return json.loads(METRICS_PATH.read_text())


# ── CLI za trening ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Trening ML modela ===")
    metrics = train()
    print("\n=== Rezultati ===")
    print(f"MAE: {metrics['mae_km']:.0f} km")
    print(f"R²:  {metrics['r2']:.3f}")
    print("\nFeature importance:")
    for feat, imp in metrics["feature_importance"].items():
        bar = "█" * int(imp * 50)
        print(f"  {feat:<25} {bar} {imp:.3f}")

    # Test predikcija
    print("\n=== Test predikcije ===")
    tests = [
        ("VW Golf diesel 2018 110kw, 85.000km", "Volkswagen", "diesel", 2018, 1968, 110, 85000, 45),
        ("Ford Fiesta benzin 2015 70kw, 120.000km", "Ford", "petrol", 2015, 1200, 70, 120000, 35),
        ("BMW 320d diesel 2020 140kw, 40.000km", "BMW", "diesel", 2020, 2000, 140, 40000, 60),
        ("Dacia Sandero benzin 2010 55kw, 180.000km", "Dacia", "petrol", 2010, 900, 55, 180000, 20),
    ]
    for label, brand, fuel, year, cc, kw, km, daily in tests:
        result = predict(brand, fuel, year, cc, kw, km, daily)
        print(f"\n  {label}")
        print(f"    → Predviđeni interval: {result['predicted_km_interval']:,} km")
        if result['days_until_service']:
            print(f"    → Predviđeni datum: {result['predicted_date']} ({result['days_until_service']} dana)")
