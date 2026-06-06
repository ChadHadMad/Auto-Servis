"""
data_generator.py — Generira realistični sintetički dataset za trening ML modela.

Modelira stvarne faktore koji utječu na servisni interval:
  - Gorivo: dizel > benzin > hibrid (dulji intervali)
  - Starost: starija vozila → kraći intervali
  - Marka: premium > economy (dulji intervali)
  - Motorizacija: veći motor → duži intervali (obično)
  - Km stanje: viši km → kraći intervali (habanje)
  - Sezona: ljeto (više km) vs zima (manje km)
  - Vozački stil: agresivna vožnja → kraći interval
"""

import numpy as np
import pandas as pd
from datetime import datetime

# ── Konfiguracija marki ────────────────────────────────────────────────────────

BRANDS = {
    # (kategorija, base_interval_km, varijabilnost)
    "Volkswagen":  ("mid",     15000, 1500),
    "BMW":         ("premium", 20000, 2000),
    "Mercedes":    ("premium", 20000, 2000),
    "Audi":        ("premium", 18000, 1800),
    "Skoda":       ("economy", 13000, 1500),
    "Ford":        ("economy", 12000, 1500),
    "Opel":        ("economy", 12000, 1500),
    "Toyota":      ("mid",     15000, 1200),
    "Honda":       ("mid",     14000, 1200),
    "Peugeot":     ("economy", 11000, 1500),
    "Renault":     ("economy", 11000, 1500),
    "Hyundai":     ("economy", 13000, 1200),
    "Kia":         ("economy", 13000, 1200),
    "Fiat":        ("economy", 10000, 1500),
    "Seat":        ("economy", 12000, 1200),
    "Mazda":       ("mid",     14000, 1200),
    "Volvo":       ("premium", 18000, 1800),
    "Dacia":       ("economy",  9000, 1500),
}

FUEL_FACTORS = {
    "diesel":  1.30,   # dizel ima dulji interval
    "petrol":  1.00,   # benzin = baseline
    "hybrid":  1.15,   # hibrid malo dulji
    "lpg":     0.85,   # LPG češće servis
}

BRAND_CATEGORIES = {
    "economy": 0.90,
    "mid":     1.00,
    "premium": 1.10,
}


def generate_dataset(n_samples: int = 6000, seed: int = 42) -> pd.DataFrame:
    """
    Generiraj sintetički dataset servisnih intervala.
    
    Svaki red = jedan servisni interval jednog vozila.
    """
    rng = np.random.default_rng(seed)
    records = []

    brand_list = list(BRANDS.keys())
    fuel_list  = list(FUEL_FACTORS.keys())
    current_year = datetime.now().year

    for _ in range(n_samples):
        # ── Karakteristike vozila ─────────────────────────────────────────────
        brand = rng.choice(brand_list)
        cat, base_interval, base_std = BRANDS[brand]

        # Gorivo — dizel češći za starija i veća vozila
        year = int(rng.integers(1998, current_year))
        age  = current_year - year

        if age > 15:
            fuel_probs = [0.55, 0.35, 0.05, 0.05]  # stariji → više dizel
        elif year >= 2018:
            fuel_probs = [0.25, 0.45, 0.25, 0.05]  # noviji → više hibrid/benzin
        else:
            fuel_probs = [0.35, 0.45, 0.15, 0.05]
        fuel = rng.choice(fuel_list, p=fuel_probs)

        # Motor
        if fuel == "diesel":
            engine_cc = int(rng.choice([1600, 1900, 2000, 2200, 2500, 3000],
                                        p=[0.15, 0.30, 0.30, 0.15, 0.07, 0.03]))
        else:
            engine_cc = int(rng.choice([1000, 1200, 1400, 1600, 1800, 2000, 2500],
                                        p=[0.10, 0.20, 0.25, 0.20, 0.12, 0.10, 0.03]))

        engine_kw = int(engine_cc * rng.uniform(0.045, 0.075))

        # ── Kontekst servisa ──────────────────────────────────────────────────
        # Km stanje pri servisu
        max_km = min(350000, age * 25000)
        total_km = int(rng.integers(5000, max(10000, max_km)))

        # Prosječni km/dan u prethodnom periodu
        # Sezonalnost: ljeto 15% više, zima 15% manje
        base_daily = rng.uniform(15, 120)
        month = int(rng.integers(1, 13))
        seasonal_factor = 1.0
        if month in [6, 7, 8]:    seasonal_factor = 1.15   # ljeto
        elif month in [12, 1, 2]: seasonal_factor = 0.87   # zima
        avg_daily_km = base_daily * seasonal_factor

        # Broj prethodnih servisa
        num_prev = int(rng.integers(0, 12))

        # Vozački stil (0=miran, 1=agresivan) — latentna varijabla
        driving_style = rng.uniform(0, 1)

        # ── Računanje target intervala ────────────────────────────────────────
        interval = base_interval

        # Faktor goriva
        interval *= FUEL_FACTORS[fuel]

        # Faktor kategorije marke
        interval *= BRAND_CATEGORIES[cat]

        # Faktor starosti — starija vozila kraći interval
        age_factor = max(0.65, 1.0 - (age - 3) * 0.015)
        interval *= age_factor

        # Faktor km stanja — viši km → kraći interval (habanje)
        km_factor = max(0.70, 1.0 - (total_km / 500000) * 0.30)
        interval *= km_factor

        # Faktor motorizacije — veći motor malo dulji interval
        kw_factor = 1.0 + (engine_kw - 75) * 0.001
        kw_factor = np.clip(kw_factor, 0.90, 1.15)
        interval *= kw_factor

        # Faktor vozačkog stila — agresivna vožnja kraći interval
        style_factor = 1.0 - driving_style * 0.20
        interval *= style_factor

        # Faktor prosječne brzine kretanja (visok daily_km → autoput → duži interval)
        if avg_daily_km > 80:      highway_factor = 1.10
        elif avg_daily_km < 25:    highway_factor = 0.90  # grad → kraći
        else:                      highway_factor = 1.00
        interval *= highway_factor

        # Šum
        noise = rng.normal(0, base_std * 0.5)
        interval = max(5000, min(40000, interval + noise))

        records.append({
            # Features
            "brand":          brand,
            "brand_category": cat,
            "fuel_type":      fuel,
            "year":           year,
            "vehicle_age":    age,
            "engine_cc":      engine_cc,
            "engine_kw":      engine_kw,
            "total_km":       total_km,
            "avg_daily_km":   round(avg_daily_km, 1),
            "month":          month,
            "num_prev_services": num_prev,
            # Target
            "km_to_next_service": int(round(interval / 500) * 500),  # zaokruži na 500
        })

    df = pd.DataFrame(records)
    print(f"[generator] Dataset: {len(df)} zapisa")
    print(f"  Intervali: min={df['km_to_next_service'].min():,} "
          f"avg={df['km_to_next_service'].mean():.0f} "
          f"max={df['km_to_next_service'].max():,} km")
    print(f"  Gorivo: {df['fuel_type'].value_counts().to_dict()}")
    return df


if __name__ == "__main__":
    df = generate_dataset(6000)
    df.to_csv("/tmp/service_dataset.csv", index=False)
    print("Saved to /tmp/service_dataset.csv")
    print(df.describe())
