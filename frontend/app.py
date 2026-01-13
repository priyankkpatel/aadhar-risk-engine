import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(layout="wide")
st.title("Aadhaar Biometric Risk Radar – India")

API = "http://127.0.0.1:8000/api/v1"

# Load available dates
df = pd.read_csv("data/processed/merged_aadhaar.csv")
dates = sorted(df["date"].unique())

date = st.slider(
    "Select Month",
    min_value=0,
    max_value=len(dates)-1,
    value=len(dates)-1
)

selected_date = dates[date]

st.subheader(f"Biometric Stress for {selected_date}")

# Call API
res = requests.get(f"{API}/risk/map?date={selected_date}")
data = pd.DataFrame(res.json())

# Load geo
geo = pd.read_csv("data/geo/district_lat_lon.csv")
data = data.merge(geo, on="district")
# Ensure CIIM is non-negative
data["CIIM"] = data["CIIM"].clip(lower=0)

# Normalize marker size for map (0.5 → 30)
data["marker_size"] = (data["CIIM"] - data["CIIM"].min()) / (data["CIIM"].max() - data["CIIM"].min() + 1e-6)
data["marker_size"] = data["marker_size"] * 30 + 5


# Plot India map
fig = px.scatter_mapbox(
    data,
    lat="lat",
    lon="lon",
    color="CIIM",
    size="CIIM",
    hover_name="district",
    zoom=4,
    mapbox_style="carto-positron",
    title="Aadhaar Biometric Dependency & Exclusion Risk"
)

st.plotly_chart(fig, use_container_width=True)

# District drill-down
district = st.selectbox("Select District", data["district"].unique())

resp = requests.get(f"{API}/risk/district/{district}")
if resp.status_code != 200 or resp.text.strip() == "":
    st.warning("No historical data available for this district.")
    st.stop()

hist = pd.DataFrame(resp.json())
if hist.empty:
    st.warning("No historical data available for this district.")
    st.stop()

st.subheader(f"Biometric Stress Trend – {district}")
st.line_chart(hist.set_index("date")["CIIM"])
