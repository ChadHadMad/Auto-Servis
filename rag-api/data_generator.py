"""
data_generator.py — Sintetički dataset za ML model servisnih intervala.

Features:
  - brand_category: economy / mid / premium
  - vehicle_age: starost vozila
  - engine_cc: obujam motora
  - engine_kw: snaga
  - total_km: ukupni km
  - avg_daily_km: prosječni km/dan
  - driving_type: city / mixed / highway
  - month: sezona
  - num_prev_services: broj servisa

Gorivo NIJE feature — ne utječe na servisni interval.
"""

import numpy as np
import pandas as pd
from datetime import datetime

BRANDS = {
    "Volkswagen":  ("mid",     15000, 1500),
    "BMW":         ("premium", 18000, 2000),
    "Mercedes":    ("premium", 18000, 2000),
    "Audi":        ("premium", 17000, 1800),
    "Skoda":       ("economy", 12000, 1500),
    "Ford":        ("economy", 11000, 1500),
    "Opel":        ("economy", 11000, 1500),
    "Toyota":      ("mid",     14000, 1200),
    "Honda":       ("mid",     13000, 1200),
    "Peugeot":     ("economy", 10000, 1500),
    "Renault":     ("economy", 10000, 1500),
    "Hyundai":     ("economy", 12000, 1200),
    "Kia":         ("economy", 12000, 1200),
    "Fiat":        ("economy",  9000, 1500),
    "Seat":        ("economy", 11000, 1200),
    "Mazda":       ("mid",     13000, 1200),
    "Volvo":       ("premium", 17000, 1800),
    "Dacia":       ("economy",  8000, 1500),
    "Iveco":       ("mid",     12000, 2000),
}

BRAND_CATEGORIES = {
    "economy": 0.90,
    "mid":     1.00,
    "premium": 1.10,
}

DRIVING_TYPES = {
    # Tip vožnje → faktor intervala
    # Grad: stop-and-go, kratke dionice → kraći interval (veće habanje)
    # Autoput: dulje dionice, čišće gorenje → duži interval
    "city":    0.85,
    "mixed":   1.00,
    "highway": 1.15,
}


def avg_daily_to_driving_type(avg_daily_km: float) -> str:
    if avg_daily_km < 30:
        return "city"
    elif avg_daily_km < 70:
        return "mixed"
    else:
        return "highway"


def generate_dataset(n_samples: int = 6000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []
    brand_list = list(BRANDS.keys())
    current_year = datetime.now().year

    for _ in range(n_samples):
        brand = rng.choice(brand_list)
        cat, base_interval, base_std = BRANDS[brand]
        year = int(rng.integers(1998, current_year))
        age  = current_year - year

        engine_cc = int(rng.choice([900, 1000, 1200, 1400, 1600, 1800, 1900,
                                     1968, 2000, 2200, 2500, 2998, 3000],
                                    p=[0.05,0.08,0.12,0.14,0.15,0.10,0.08,
                                       0.08,0.08,0.05,0.04,0.02,0.01]))
        engine_kw = int(engine_cc * rng.uniform(0.045, 0.075))

        max_km = min(400000, age * 28000)
        total_km = int(rng.integers(5000, max(10000, max_km)))

        # Tip vožnje i km/dan
        driving_type = rng.choice(["city", "mixed", "highway"], p=[0.30, 0.45, 0.25])
        if driving_type == "city":
            base_daily = rng.uniform(10, 30)
        elif driving_type == "mixed":
            base_daily = rng.uniform(25, 70)
        else:
            base_daily = rng.uniform(60, 150)

        # Sezonalnost
        month = int(rng.integers(1, 13))
        if month in [6, 7, 8]:    seasonal = 1.12
        elif month in [12, 1, 2]: seasonal = 0.88
        else:                      seasonal = 1.00
        avg_daily_km = base_daily * seasonal

        num_prev = int(rng.integers(0, 12))

        # ── Izračun intervala ────────────────────────────────────────────────
        interval = base_interval

        # Kategorija marke (premium → duži interval)
        interval *= BRAND_CATEGORIES[cat]

        # Starost vozila (starije → kraći interval)
        age_factor = max(0.65, 1.0 - max(0, age - 3) * 0.015)
        interval *= age_factor

        # Ukupni km (više km → kraći interval zbog habanja)
        km_factor = max(0.70, 1.0 - (total_km / 500000) * 0.30)
        interval *= km_factor

        # Tip vožnje (grad → kraći, autoput → duži)
        interval *= DRIVING_TYPES[driving_type]

        # Šum
        noise = rng.normal(0, base_std * 0.5)
        interval = max(5000, min(35000, interval + noise))

        records.append({
            "brand":             brand,
            "brand_category":    cat,
            "vehicle_age":       age,
            "engine_cc":         engine_cc,
            "engine_kw":         engine_kw,
            "total_km":          total_km,
            "avg_daily_km":      round(avg_daily_km, 1),
            "driving_type":      driving_type,
            "month":             month,
            "num_prev_services": num_prev,
            "km_to_next_service": int(round(interval / 500) * 500),
        })

    df = pd.DataFrame(records)
    print(f"[generator] Dataset: {len(df)} zapisa")
    print(f"  Intervali: min={df['km_to_next_service'].min():,} "
          f"avg={df['km_to_next_service'].mean():.0f} "
          f"max={df['km_to_next_service'].max():,} km")
    print(f"  Driving: {df['driving_type'].value_counts().to_dict()}")
    return df


if __name__ == "__main__":
    df = generate_dataset(6000)
    print(df.describe())