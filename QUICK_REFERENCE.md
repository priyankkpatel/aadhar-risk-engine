# Quick Reference: Aadhaar Risk System

## What This System Does

Monitors Aadhaar (India's identity system) to predict when and where problems might occur. Helps government officials prevent identity failures before they affect citizens.

## Key Metrics Explained

| Metric | What It Means | Policy Impact |
|--------|---------------|---------------|
| **CIIM** (0-100) | Overall risk score. Higher = more vulnerable | > 70 = EMERGENCY, > 50 = HIGH |
| **Biometric Intensity** (%) | % of citizens dependent on biometrics | > 60% = need alternative access |
| **Child Biometric Ratio** (%) | % of biometric users who are children | > 10% = protect children priority |
| **Growth Direction** | Is dependency increasing or decreasing? | INCREASING = audit needed |
| **TTF** (months) | Time until high-risk conditions develop | < 6 months = urgent intervention |

## Policy Flags (Priority Order)

1. 🔴 **EMERGENCY** - CIIM > 70. Immediate UIDAI action needed.
2. 🟠 **PROTECT_CHILDREN** - Child ratio > 10%. Enable non-biometric alternatives.
3. 🟡 **AUDIT_EXPANSION** - Growth > 30%. Review enrollment practices.
4. 🟢 **NORMAL** - Risk levels acceptable. Continue monitoring.

## Recommended Actions

| Risk Driver | Recommended Intervention |
|-------------|--------------------------|
| High child ratio (>30%) | Enable OTP/face recognition for children |
| High biometric intensity (>60%) | Expand assisted centers and offline KYC |
| Rapid growth (>5%/month) | Audit device quality and operator training |
| High CIIM (>60) | Coordinate UIDAI and State Government |

## Key Improvements Made

✅ **Stable Growth Metrics**: 3-month rolling averages reduce noise  
✅ **Better Edge Cases**: Handles small districts and missing data  
✅ **Clearer Labels**: "Citizens Dependent on Biometrics" not "biometric intensity"  
✅ **Improved Formulas**: Negative growth (good) doesn't penalize CIIM  
✅ **Priority Flags**: EMERGENCY always shows when applicable  

## System Strengths

- ✅ Simple, explainable formulas (no black boxes)
- ✅ Actionable policy flags
- ✅ Human impact focus (citizens/children at risk)
- ✅ Geographic visualization

## Areas to Monitor

- ⚠️ New districts with sparse data
- ⚠️ Districts with < 100 enrollments (marked as insufficient data)
- ⚠️ Suspicious patterns (100% biometric intensity = flagged for review)
