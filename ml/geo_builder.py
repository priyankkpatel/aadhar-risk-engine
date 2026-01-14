import pandas as pd

print("Loading India Post geo data...")

raw = pd.read_csv("data/geo/india_post_raw.csv")
raw.columns = raw.columns.str.strip().str.lower()

geo = raw[["district", "latitude", "longitude"]]
geo.columns = ["district", "lat", "lon"]

# Normalize district names
geo["district"] = geo["district"].astype(str).str.strip().str.upper()

# Convert to numeric
geo["lat"] = pd.to_numeric(geo["lat"], errors="coerce")
geo["lon"] = pd.to_numeric(geo["lon"], errors="coerce")

# HARD FILTER to India bounding box
geo = geo[
    (geo["lat"] >= 6) & (geo["lat"] <= 36) &
    (geo["lon"] >= 68) & (geo["lon"] <= 98)
]

# Drop invalid
geo = geo.dropna(subset=["lat","lon","district"])

# Average PIN codes to district
geo = geo.groupby("district")[["lat","lon"]].mean().reset_index()

geo.to_csv("data/geo/district_lat_lon.csv", index=False)

print("Geo file saved with", len(geo), "districts.")
