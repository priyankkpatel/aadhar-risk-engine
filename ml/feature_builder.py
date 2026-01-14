import pandas as pd
from backend.data_access.loader import load_biometric, load_enrolment, load_demographic

def build_features():
    print("Loading Aadhaar datasets...")
    bio = load_biometric()
    enr = load_enrolment()
    demo = load_demographic()

    # Standardize
    for df in [bio, enr, demo]:
        df["district"] = df["district"].str.strip().str.title()
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    bio = bio.dropna(subset=["date"])
    enr = enr.dropna(subset=["date"])
    demo = demo.dropna(subset=["date"])

    print("Merging datasets...")
    df = bio.merge(enr, on=["date","district","pincode"])
    df = df.merge(demo, on=["date","district","pincode"])

    print("Building biometric dependency indicators...")

    # Total biometric usage
    df["total_bio"] = df["bio_age_5_17"] + df["bio_age_17_"]

    # Total population enrolled
    df["total_enrolled"] = df["age_0_5"] + df["age_5_17"] + df["age_18_greater"]

    # How dependent a district is on biometrics
    df["biometric_intensity"] = df["total_bio"] / df["total_enrolled"]

    # Vulnerable biometric use
    df["child_bio_ratio"] = df["bio_age_5_17"] / df["total_bio"]

    # Biometric growth (stress)
    df["bio_growth"] = df.groupby("district")["biometric_intensity"].diff()

    # Exclusion risk
    df["exclusion_risk"] = df["child_bio_ratio"] * df["biometric_intensity"]

    # CIIM Risk Index
    df["CIIM"] = (
        0.5 * df["biometric_intensity"]
        + 0.3 * df["bio_growth"]
        + 0.2 * df["exclusion_risk"]
    ).clip(lower=0)

    df["district"] = df["district"].str.upper().str.strip()

    df.to_csv("data/processed/merged_aadhaar.csv", index=False)
    print("CIIM Aadhaar Risk Table created successfully.")

if __name__ == "__main__":
    build_features()
