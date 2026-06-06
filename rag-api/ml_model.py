"""
ml_model.py — ML model za predikciju km do sljedećeg servisa.

Features (gorivo NIJE uključeno — ne utječe na servisni interval):
  - brand_category: economy / mid / premium
  - driving_type:   city / mixed / highway  ← novi, zamjenjuje fuel_type
  - vehicle_age
  - engine_cc, engine_kw
  - total_km
  - avg_daily_km
  - month
  - num_prev_services
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OrdinalEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from data_generator import generate_dataset, avg_daily_to_driving_type

MODEL_PATH     = Path("/app/data/service_model.joblib")
METRICS_PATH   = Path("/app/data/model_metrics.json")
REAL_DATA_PATH = Path("/app/data/real_training_data.csv")

CATEGORICAL_FEATURES = ["brand_category", "driving_type"]
NUMERICAL_FEATURES   = [
    "vehicle_age", "engine_cc", "engine_kw",
    "total_km", "avg_daily_km", "month", "num_prev_services",
]
ALL_FEATURES = CATEGORICAL_FEATURES + NUMERICAL_FEATURES
TARGET = "km_to_next_service"

BRAND_CATS    = ["economy", "mid", "premium"]
DRIVING_TYPES = ["city", "mixed", "highway"]

BRAND_CATEGORY_MAP = {
    "volkswagen": "mid",   "vw": "mid",
    "bmw": "premium",      "mercedes": "premium",  "audi": "premium",
    "volvo": "premium",    "lexus": "premium",
    "skoda": "economy",    "ford": "economy",       "opel": "economy",
    "peugeot": "economy",  "renault": "economy",    "fiat": "economy",
    "seat": "economy",     "dacia": "economy",      "hyundai": "economy",
    "kia": "economy",      "iveco": "mid",
    "toyota": "mid",       "honda": "mid",          "mazda": "mid",
    "nissan": "mid",       "subaru": "mid",
}


def _brand_to_category(brand: str) -> str:
    return BRAND_CATEGORY_MAP.get(brand.lower().strip(), "mid")


def _build_pipeline() -> Pipeline:
    cat_transformer = OrdinalEncoder(
        categories=[BRAND_CATS, DRIVING_TYPES],
        handle_unknown="use_encoded_value",
        unknown_value=-1,
    )
    preprocessor = ColumnTransformer([
        ("cat", cat_transformer, CATEGORICAL_FEATURES),
        ("num", StandardScaler(), NUMERICAL_FEATURES),
    ])
    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.08,
        min_samples_leaf=10,
        subsample=0.8,
        random_state=42,
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def train(n_synthetic: int = 6000, real_data_weight: float = 5.0) -> dict:
    print("[ml_model] Generiranje sintetičkog dataseta...")
    df_synth = generate_dataset(n_synthetic)

    frames = [df_synth]
    n_real_count = 0

    if REAL_DATA_PATH.exists():
        df_real = pd.read_csv(REAL_DATA_PATH)
        if len(df_real) > 0:
            n_real_count = len(df_real)
            print(f"[ml_model] Stvarni podaci: {n_real_count} zapisa (težina x{real_data_weight:.0f})")
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

    print(f"[ml_model] Trening: {len(X_train)} | Test: {len(X_test)}")
    print("[ml_model] Treniranje modela...")

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)
    print(f"[ml_model] MAE: {mae:.0f} km | R²: {r2:.3f}")

    feat_importance = dict(zip(
        ALL_FEATURES,
        pipeline.named_steps["model"].feature_importances_.tolist()
    ))
    sorted_fi = dict(sorted(feat_importance.items(), key=lambda x: x[1], reverse=True))
    print(f"[ml_model] Top features: {list(sorted_fi.keys())[:4]}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    metrics = {
        "trained_at":        datetime.utcnow().isoformat(),
        "n_synthetic":       n_synthetic,
        "n_real":            n_real_count,
        "n_total":           len(df),
        "mae_km":            round(mae, 0),
        "r2":                round(r2, 3),
        "feature_importance": {k: round(v, 4) for k, v in sorted_fi.items()},
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    print(f"[ml_model] Model spreman: {MODEL_PATH}")
    return metrics


def load_model():
    if not MODEL_PATH.exists():
        print("[ml_model] Model ne postoji — treniram...")
        train()
    return joblib.load(MODEL_PATH)


def predict(
    brand: str,
    avg_daily_km: float,
    year: int,
    engine_cc: int,
    engine_kw: int,
    total_km: int,
    num_prev_services: int = 0,
    month: int = None,
    # fuel_type zadržan zbog kompatibilnosti s postojećim pozivima, ali se ignorira
    fuel_type: str = None,
) -> dict:
    if month is None:
        month = datetime.now().month

    pipeline     = load_model()
    brand_cat    = _brand_to_category(brand)
    vehicle_age  = datetime.now().year - year
    driving_type = avg_daily_to_driving_type(avg_daily_km)

    row = pd.DataFrame([{
        "brand_category":    brand_cat,
        "driving_type":      driving_type,
        "vehicle_age":       vehicle_age,
        "engine_cc":         engine_cc,
        "engine_kw":         engine_kw,
        "total_km":          total_km,
        "avg_daily_km":      avg_daily_km,
        "month":             month,
        "num_prev_services": num_prev_services,
    }])

    predicted_km = int(pipeline.predict(row)[0])
    predicted_km = round(predicted_km / 500) * 500
    predicted_km = max(5000, min(35000, predicted_km))

    days_until     = None
    predicted_date = None
    if avg_daily_km > 0:
        days_until     = int(predicted_km / avg_daily_km)
        predicted_date = (date.today() + timedelta(days=days_until)).isoformat()

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
            "brand":        brand,
            "brand_category": brand_cat,
            "driving_type": driving_type,
            "vehicle_age":  vehicle_age,
            "engine_cc":    engine_cc,
            "engine_kw":    engine_kw,
            "total_km":     total_km,
            "avg_daily_km": avg_daily_km,
        },
    }


def add_real_datapoint(
    brand: str,
    avg_daily_km: float,
    year: int,
    engine_cc: int,
    engine_kw: int,
    total_km_at_service: int,
    num_prev_services: int,
    actual_km_interval: int,
    month: int = None,
    # fuel_type ignoriran
    fuel_type: str = None,
) -> int:
    if month is None:
        month = datetime.now().month

    brand_cat    = _brand_to_category(brand)
    vehicle_age  = datetime.now().year - year
    driving_type = avg_daily_to_driving_type(avg_daily_km)

    row = {
        "brand_category":    brand_cat,
        "driving_type":      driving_type,
        "vehicle_age":       vehicle_age,
        "engine_cc":         engine_cc,
        "engine_kw":         engine_kw,
        "total_km":          total_km_at_service,
        "avg_daily_km":      round(avg_daily_km, 1),
        "month":             month,
        "num_prev_services": num_prev_services,
        "km_to_next_service": actual_km_interval,
        "added_at":          datetime.utcnow().isoformat(),
    }

    REAL_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_new = pd.DataFrame([row])

    if REAL_DATA_PATH.exists():
        df_existing = pd.read_csv(REAL_DATA_PATH)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(REAL_DATA_PATH, index=False)
    n_real = len(df_combined)
    print(f"[ml_model] Real datapoint dodan. Ukupno: {n_real}")

    if n_real % 10 == 0:
        print(f"[ml_model] Auto-retrening na {n_real} stvarnih zapisa...")
        train()

    return n_real


def get_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {"status": "model nije treniran"}
    return json.loads(METRICS_PATH.read_text())


if __name__ == "__main__":
    print("=== Trening ML modela (bez fuel_type) ===")
    metrics = train()
    print(f"\nMAE: {metrics['mae_km']:.0f} km | R²: {metrics['r2']:.3f}")
    print("\nFeature importance:")
    for feat, imp in metrics["feature_importance"].items():
        bar = "█" * int(imp * 50)
        print(f"  {feat:<25} {bar} {imp:.3f}")

    print("\n=== Test predikcije ===")
    tests = [
        ("VW Golf 2018, 131k km, 49 km/dan",  "Volkswagen", 49,  2018, 1968, 110, 131000, 4),
        ("Renault Trafic 2005, 246k, 35/dan",  "Renault",    35,  2005, 1870,  74, 246000, 12),
        ("Iveco Daily 2008, 239k, 30/dan",     "Iveco",      30,  2008, 2998, 130, 239350, 8),
        ("Toyota Aygo 2015, 108k, 25/dan",     "Toyota",     25,  2015,  998,  51, 108000, 3),
    ]
    for label, brand, daily, year, cc, kw, km, prev in tests:
        r = predict(brand, daily, year, cc, kw, km, prev)
        print(f"\n  {label}")
        print(f"    driving_type: {r['input_features']['driving_type']}")
        print(f"    → Interval: {r['predicted_km_interval']:,} km")
        print(f"    → Datum:    {r['predicted_date']} ({r['days_until_service']} dana)")