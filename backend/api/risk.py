from fastapi import APIRouter
import pandas as pd

router = APIRouter()

DATA = "data/processed/merged_aadhaar.csv"

@router.get("/risk/map")
def risk_map(date: str):
    df = pd.read_csv(DATA)
    df = df[df["date"] == date]

    return df[[
        "district","state","CIIM",
        "biometric_intensity",
        "child_bio_ratio",
        "bio_growth"
    ]].to_dict(orient="records")


@router.get("/risk/district/{district}")
def district_risk(district: str):
    df = pd.read_csv(DATA)

    # normalize
    df["district"] = df["district"].str.strip().str.lower()
    district = district.strip().lower()

    d = df[df["district"] == district]

    if len(d) == 0:
        return []

    return d.sort_values("date").to_dict(orient="records")

