import pandas as pd
import numpy as np
from backend.data_access.loader import (
    load_biometric,
    load_enrolment,
    load_demographic
)

# -----------------------------------
# CONFIG
# -----------------------------------
BASE_TIME = 12        # months (policy assumption)
MAX_TTF = 24          # stable upper bound
MIN_ENROLLMENT = 100  # minimum enrollments for reliable metrics
ROLLING_WINDOW = 3    # months for rolling average smoothing


def build_features():
    print("Loading Aadhaar datasets...")

    bio = load_biometric()
    enr = load_enrolment()
    demo = load_demographic()

    # -----------------------------------
    # STANDARDIZE KEYS
    # -----------------------------------
    for df in [bio, enr, demo]:
        df["district"] = df["district"].str.strip().str.title()
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    bio = bio.dropna(subset=["date"])
    enr = enr.dropna(subset=["date"])
    demo = demo.dropna(subset=["date"])

    # -----------------------------------
    # MERGE DATASETS
    # -----------------------------------
    print("Merging datasets...")
    df = bio.merge(enr, on=["date", "district", "pincode"], how="inner")
    df = df.merge(demo, on=["date", "district", "pincode"], how="inner")

    print("Building biometric dependency indicators...")

    # -----------------------------------
    # CORE COUNTS
    # -----------------------------------
    df["total_bio"] = df["bio_age_5_17"] + df["bio_age_17_"]
    df["total_enrolled"] = (
        df["age_0_5"] + df["age_5_17"] + df["age_18_greater"]
    )

    # -----------------------------------
    # DATA QUALITY CHECKS (OPTIMIZED)
    # -----------------------------------
    # Remove invalid rows (optimize with vectorized operations)
    initial_count = len(df)
    df = df[(df["total_enrolled"] > 0) & (df["total_bio"] > 0)].copy()
    removed_count = initial_count - len(df)
    if removed_count > 0:
        print(f"  Removed {removed_count} rows with invalid enrollment/biometric data")
    
    # -----------------------------------
    # BIOMETRIC INTENSITY (CALCULATE BEFORE QUALITY CHECKS)
    # -----------------------------------
    df["biometric_intensity"] = df["total_bio"] / df["total_enrolled"]
    df["biometric_intensity"] = df["biometric_intensity"].clip(0, 1)
    
    # -----------------------------------
    # DATA QUALITY FLAGS (AFTER INTENSITY CALCULATION)
    # -----------------------------------
    # Flag districts with very small enrollment (unreliable metrics)
    df["has_sufficient_data"] = df["total_enrolled"] >= MIN_ENROLLMENT
    
    # Flag suspicious data patterns (100% biometric intensity is unrealistic)
    # Also flag if biometrics exceed enrolled (data inconsistency)
    df["data_quality_flag"] = "OK"
    df.loc[df["biometric_intensity"] > 0.99, "data_quality_flag"] = "SUSPICIOUS"
    df.loc[df["total_bio"] > df["total_enrolled"], "data_quality_flag"] = "DATA_INCONSISTENT"
    df.loc[~df["has_sufficient_data"], "data_quality_flag"] = "INSUFFICIENT_DATA"
    
    # Log data quality issues
    suspicious_count = (df["data_quality_flag"] == "SUSPICIOUS").sum()
    insufficient_count = (df["data_quality_flag"] == "INSUFFICIENT_DATA").sum()
    if suspicious_count > 0:
        print(f"  ⚠️  Flagged {suspicious_count} districts with suspicious data patterns")
    if insufficient_count > 0:
        print(f"  ⚠️  Flagged {insufficient_count} districts with insufficient data (<{MIN_ENROLLMENT} enrollments)")

    # -----------------------------------
    # CHILD BIOMETRIC RISK
    # -----------------------------------
    df["child_bio_ratio"] = df["bio_age_5_17"] / df["total_bio"]
    df["child_bio_ratio"] = df["child_bio_ratio"].clip(0, 1)

    # -----------------------------------
    # BIOMETRIC GROWTH (STABILIZED WITH ROLLING AVERAGE) - OPTIMIZED
    # -----------------------------------
    # Sort once for efficient groupby operations
    df = df.sort_values(["district", "date"]).copy()
    
    # Calculate month-to-month change (raw growth) - optimized vectorized operation
    df["bio_growth_raw"] = df.groupby("district")["biometric_intensity"].diff()
    df["bio_growth_raw"] = df["bio_growth_raw"].fillna(0)
    
    # Use rolling average to smooth out noise (more stable indicator)
    # Optimize: Use transform for better performance with large datasets
    df["bio_growth"] = (
        df.groupby("district")["bio_growth_raw"]
        .transform(lambda x: x.rolling(window=ROLLING_WINDOW, min_periods=1).mean())
    )
    df["bio_growth"] = df["bio_growth"].fillna(df["bio_growth_raw"])
    
    # Clip outliers (extreme growth changes likely due to data errors or campaigns)
    df["bio_growth"] = df["bio_growth"].clip(-0.5, 0.5)
    
    # Additional validation: flag extreme growth as potentially unreliable
    df["growth_reliability"] = "RELIABLE"
    extreme_growth = abs(df["bio_growth"]) > 0.3
    df.loc[extreme_growth, "growth_reliability"] = "EXTREME_GROWTH_CHECK_NEEDED"
    
    # Growth direction indicator (for interpretability)
    df["growth_direction"] = "STABLE"
    df.loc[df["bio_growth"] > 0.05, "growth_direction"] = "INCREASING"
    df.loc[df["bio_growth"] < -0.05, "growth_direction"] = "DECREASING"

    # -----------------------------------
    # EXCLUSION RISK
    # -----------------------------------
    df["exclusion_risk"] = (
        df["child_bio_ratio"] * df["biometric_intensity"]
    )

    # -----------------------------------
    # CIIM INDEX (IMPROVED - HANDLES NEGATIVE GROWTH) - OPTIMIZED
    # -----------------------------------
    # Separate positive growth (bad) from negative growth (good)
    # Only penalize for increasing dependency, not decreasing
    bio_growth_penalty = df["bio_growth"].clip(lower=0)  # Only positive growth counts as risk
    
    # Calculate CIIM with optimized vectorized operations
    df["CIIM"] = (
        0.5 * df["biometric_intensity"]
        + 0.3 * bio_growth_penalty
        + 0.2 * df["exclusion_risk"]
    )
    
    # Ensure CIIM stays in [0, 1] range (clamp for safety)
    df["CIIM"] = df["CIIM"].clip(0, 1)
    
    # Add CIIM percentile for comparison (normalized rank)
    # Use rank() instead of qcut for better performance and handling of duplicates
    def calc_percentile(series):
        if len(series) < 2:
            return 50
        return (series.rank(pct=True) * 100).round(1)
    
    df["CIIM_percentile"] = df.groupby("date")["CIIM"].transform(calc_percentile)
    df["CIIM_percentile"] = df["CIIM_percentile"].fillna(50)  # Default to median if can't calculate
    
    # Round CIIM for cleaner output (4 decimal places)
    df["CIIM"] = df["CIIM"].round(4)

    # -----------------------------------
    # TIME TO FAILURE (IMPROVED - MORE STABLE) - OPTIMIZED
    # -----------------------------------
    # Only consider positive growth as accelerating risk
    # Negative growth (decreasing dependency) extends time-to-failure
    growth_factor = 1 + df["bio_growth"].clip(lower=0)  # Only positive growth accelerates
    
    # Use a more stable denominator with better handling of edge cases
    # Avoid division by zero with minimum intensity threshold
    intensity_weighted = df["biometric_intensity"] * growth_factor
    min_intensity_threshold = 0.01  # Minimum intensity for meaningful calculation
    
    # Use improved formula: TTF = BASE_TIME / (adjusted_intensity + epsilon)
    # Adjusted intensity accounts for both current level and growth trend
    adjusted_intensity = np.maximum(intensity_weighted, min_intensity_threshold)
    df["TTF"] = BASE_TIME / (adjusted_intensity + 1e-3)
    
    # For districts with low intensity and decreasing growth, extend TTF
    # (These districts are improving and have more time)
    low_intensity_decreasing = (df["biometric_intensity"] < 0.2) & (df["bio_growth"] < -0.05)
    df.loc[low_intensity_decreasing, "TTF"] = df.loc[low_intensity_decreasing, "TTF"] * 1.5
    
    # For districts with very high intensity, reduce TTF more aggressively
    high_intensity_increasing = (df["biometric_intensity"] > 0.7) & (df["bio_growth"] > 0.1)
    df.loc[high_intensity_increasing, "TTF"] = df.loc[high_intensity_increasing, "TTF"] * 0.8
    
    df["TTF"] = df["TTF"].clip(lower=1, upper=MAX_TTF)
    df["TTF"] = df["TTF"].round(2)  # Round to 2 decimal places for cleaner output

    # -----------------------------------
    # CIIM ACCELERATION (EARLY WARNING) - SMOOTHED & OPTIMIZED
    # -----------------------------------
    # Calculate acceleration (second derivative of CIIM)
    df["CIIM_ACCEL"] = (
        df.groupby("district")["CIIM"].diff().fillna(0)
    )
    
    # Smooth acceleration with rolling average (optimized with transform)
    df["CIIM_ACCEL"] = (
        df.groupby("district")["CIIM_ACCEL"]
        .transform(lambda x: x.rolling(window=ROLLING_WINDOW, min_periods=1).mean())
    )
    df["CIIM_ACCEL"] = df["CIIM_ACCEL"].fillna(0)
    
    # Trend indicator (3-month trend) - optimized calculation
    def calculate_trend(series):
        if len(series) < 2:
            return 0
        first = series.iloc[0]
        last = series.iloc[-1]
        if last > first * 1.1:  # 10% increase
            return 1
        elif last < first * 0.9:  # 10% decrease
            return -1
        else:
            return 0
    
    df["CIIM_trend_3mo"] = (
        df.groupby("district")["CIIM"]
        .transform(lambda x: x.rolling(window=3, min_periods=2).apply(calculate_trend, raw=False))
    )
    df["CIIM_trend_3mo"] = df["CIIM_trend_3mo"].fillna(0).astype(int)

    # -----------------------------------
    # HUMAN IMPACT
    # -----------------------------------
    df["citizens_at_risk"] = (
        df["total_enrolled"] * df["biometric_intensity"]
    )

    df["children_at_risk"] = (
        df["citizens_at_risk"] * df["child_bio_ratio"]
    )

    # -----------------------------------
    # POLICY RULE ENGINE (PRIORITY-BASED)
    # -----------------------------------
    # Initialize with NORMAL, then apply flags in priority order
    # Priority: EMERGENCY > PROTECT_CHILDREN > AUDIT_EXPANSION > NORMAL
    df["policy_flag"] = "NORMAL"

    # Priority 3: Audit expansion (rapid growth needs review)
    df.loc[df["bio_growth"] > 0.3, "policy_flag"] = "AUDIT_EXPANSION"
    
    # Priority 2: Protect children (child biometric ratio too high)
    df.loc[df["child_bio_ratio"] > 0.1, "policy_flag"] = "PROTECT_CHILDREN"
    
    # Priority 1: Emergency (critical CIIM score)
    df.loc[df["CIIM"] > 0.7, "policy_flag"] = "EMERGENCY"
    
    # Override: If data quality is poor, flag for data review
    df.loc[df["data_quality_flag"] == "SUSPICIOUS", "policy_flag"] = "DATA_REVIEW"

    # -----------------------------------
    # FINAL CLEANUP & VALIDATION (CRITICAL)
    # -----------------------------------
    # Fill missing values with safe defaults (optimized with fillna in place)
    critical_columns = {
        "CIIM": 0,
        "TTF": MAX_TTF,
        "bio_growth": 0,
        "biometric_intensity": 0,
        "child_bio_ratio": 0,
        "exclusion_risk": 0,
        "bio_growth_raw": 0,
        "CIIM_ACCEL": 0,
        "CIIM_trend_3mo": 0
    }
    
    for col, default_val in critical_columns.items():
        if col in df.columns:
            df[col] = df[col].fillna(default_val)
    
    # Ensure all risk metrics are in valid ranges (vectorized operations)
    df["CIIM"] = df["CIIM"].clip(0, 1)
    df["biometric_intensity"] = df["biometric_intensity"].clip(0, 1)
    df["child_bio_ratio"] = df["child_bio_ratio"].clip(0, 1)
    df["exclusion_risk"] = df["exclusion_risk"].clip(0, 1)
    df["TTF"] = df["TTF"].clip(1, MAX_TTF)
    df["bio_growth"] = df["bio_growth"].clip(-0.5, 0.5)

    # Normalize district names (optimized)
    df["district"] = df["district"].str.upper().str.strip()
    
    # Final data quality check
    invalid_rows = df[df["CIIM"].isna() | df["TTF"].isna() | df["biometric_intensity"].isna()]
    if len(invalid_rows) > 0:
        print(f"  ⚠️  WARNING: {len(invalid_rows)} rows still have missing critical values after cleanup")
        # Drop rows with critical missing values as last resort
        df = df.dropna(subset=["CIIM", "TTF", "biometric_intensity"])
    
    # -----------------------------------
    # SAVE OUTPUT (OPTIMIZED)
    # -----------------------------------
    output_path = "data/processed/merged_aadhaar.csv"
    df.to_csv(output_path, index=False)
    
    # Summary statistics
    print(f"\n✅ CIIM Aadhaar Risk Table created successfully!")
    print(f"   📊 Total records: {len(df):,}")
    print(f"   📅 Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   📍 Unique districts: {df['district'].nunique():,}")
    if "state" in df.columns:
        print(f"   🏛️  Unique states: {df['state'].nunique():,}")
    print(f"   📈 Average CIIM: {df['CIIM'].mean():.3f}")
    print(f"   ⏳ Average TTF: {df['TTF'].mean():.1f} months")
    print(f"   📁 Saved to: {output_path}")


if __name__ == "__main__":
    build_features()
