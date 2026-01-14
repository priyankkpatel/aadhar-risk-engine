import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(layout="wide")
st.title("Aadhaar Biometric Risk Radar – India")

API = "http://127.0.0.1:8000/api/v1"

# Load available dates
df = pd.read_csv("data/processed/merged_aadhaar.csv")
dates = sorted(df["date"].astype(str).unique())

date_idx = st.slider(
    "Select Month",
    min_value=0,
    max_value=len(dates) - 1,
    value=len(dates) - 1
)

selected_date = dates[date_idx]
st.subheader(f"Biometric Stress for {selected_date}")

# Call API
res = requests.get(f"{API}/risk/map?date={selected_date}")
data = pd.DataFrame(res.json())

if data.empty:
    st.warning("No Aadhaar data available for this date.")
    st.stop()

# Load geo
geo = pd.read_csv("data/geo/district_lat_lon.csv")
data = data.merge(geo, on="district", how="left")

# Ensure CIIM is valid
data["CIIM"] = pd.to_numeric(data["CIIM"], errors="coerce").fillna(0).clip(lower=0)

# Marker size for map
data["marker_size"] = (
    (data["CIIM"] - data["CIIM"].min())
    / (data["CIIM"].max() - data["CIIM"].min() + 1e-6)
) * 30 + 5

# India Map
fig = px.scatter_map(
    data,
    lat="lat",
    lon="lon",
    color="CIIM",
    size="marker_size",
    hover_name="district",
    zoom=4,
    map_style="carto-positron",
    title="Aadhaar Biometric Dependency & Exclusion Risk"
)

st.plotly_chart(fig, use_container_width=True)

# District selection
district = st.selectbox("Select District", sorted(data["district"].dropna().unique()))

# Extract district row
row = data[data["district"] == district].iloc[0]

biometric_intensity = row["biometric_intensity"]
child_ratio = row["child_bio_ratio"]
growth = row["bio_growth"]
ciim = row["CIIM"]

# Risk tier
if ciim > 0.7:
    risk_level = "CRITICAL"
elif ciim > 0.5:
    risk_level = "HIGH"
elif ciim > 0.3:
    risk_level = "MEDIUM"
else:
    risk_level = "LOW"

st.markdown("## 🧠 District Risk Analysis")
st.write(f"**CIIM Risk Level:** {risk_level}")

st.markdown("### 📊 Risk Drivers")
st.write(f"**Biometric Intensity:** {biometric_intensity:.2f}")
st.write(f"**Child Biometric Ratio:** {child_ratio:.2f}")
st.write(f"**Biometric Growth:** {growth:.2f}")

st.markdown("## 🛠 Recommended Actions")

actions = []

if child_ratio > 0.3:
    actions.append("Deploy non-biometric Aadhaar options for children (OTP, face, assisted modes).")

if biometric_intensity > 0.6:
    actions.append("Increase assisted Aadhaar centers and offline KYC facilities.")

if growth > 0.05:
    actions.append("Audit rapid biometric expansion — check devices and operator practices.")

if ciim > 0.6:
    actions.append("Trigger UIDAI and State Government intervention in this district.")

if not actions:
    actions.append("No immediate intervention required.")

for a in actions:
    st.write("•", a)
