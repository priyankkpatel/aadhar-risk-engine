import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from ml.action_simulator import simulate


st.set_page_config(
    layout="wide", 
    page_title="Aadhaar Risk Prevention Dashboard",
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .risk-critical { background-color: #ffcccc; }
    .risk-high { background-color: #ffe6cc; }
    .risk-medium { background-color: #ffffcc; }
    .risk-low { background-color: #ccffcc; }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🛡️ Aadhaar Digital Identity Risk & Failure Prevention System</h1>', unsafe_allow_html=True)
st.caption("**Early warning system for Aadhaar access risks across India** - Real-time district-level risk monitoring")

API = "http://127.0.0.1:8000/api/v1"

with st.sidebar:
    st.header("⚙️ Dashboard Controls")
    
    # Load data once
    if 'df' not in st.session_state:
        st.session_state.df = pd.read_csv("data/processed/merged_aadhaar.csv")
    
    df = st.session_state.df
    dates = sorted(df["date"].astype(str).unique()) if not df.empty else []
    
    if dates:
        selected_date = st.selectbox(
            "📅 Select Assessment Month",
            options=dates,
            index=len(dates) - 1,
            help="Choose a month to analyze risk levels"
        )
        
        # State filter
        states = sorted(df["state"].dropna().unique()) if "state" in df.columns else []
        if states:
            selected_state = st.selectbox(
                "🏛️ Filter by State (Optional)",
                options=["All States"] + states,
                help="Filter districts by state"
            )
        else:
            selected_state = "All States"
    else:
        st.error("No data available. Please run feature_builder.py first.")
        st.stop()

# Use direct data access for better performance
data = df[df["date"] == selected_date].copy()

if data.empty:
    st.warning("⚠️ No Aadhaar data available for this date.")
    st.stop()

# Filter by state if selected
if selected_state != "All States":
    data = data[data["state"] == selected_state].copy()
    if data.empty:
        st.warning(f"⚠️ No data available for {selected_state} on {selected_date}.")
        st.stop()

# Merge geo data
try:
    geo = pd.read_csv("data/geo/district_lat_lon.csv")
    data = data.merge(geo, on="district", how="left")
except Exception as e:
    st.warning(f"⚠️ Could not load geographic data: {e}")

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_districts = len(data)
    st.metric("📍 Total Districts", f"{total_districts:,}", help="Number of districts in current view")

with col2:
    avg_ciim = data["CIIM"].mean() if "CIIM" in data.columns else 0
    st.metric("📊 Avg CIIM Score", f"{avg_ciim*100:.1f}", delta=None, help="Average risk score across all districts")

with col3:
    critical_count = len(data[data["CIIM"] > 0.7]) if "CIIM" in data.columns else 0
    st.metric("🔴 Critical Districts", f"{critical_count}", 
              delta=f"{critical_count - len(data[data['CIIM'] > 0.7])}" if critical_count > 0 else None,
              help="Districts with CIIM > 70 (Emergency level)")

with col4:
    high_risk_count = len(data[(data["CIIM"] > 0.5) & (data["CIIM"] <= 0.7)]) if "CIIM" in data.columns else 0
    st.metric("🟠 High Risk Districts", f"{high_risk_count}", help="Districts with CIIM 50-70")

st.markdown("---")

st.markdown("## 🗺️ Geographic Risk Distribution")

# Clean and prepare data for map
if "CIIM" in data.columns:
    data["CIIM"] = pd.to_numeric(data["CIIM"], errors="coerce").fillna(0).clip(0, 1)
    
    # Calculate marker size (normalized)
    if data["CIIM"].max() > data["CIIM"].min():
        data["marker_size"] = (
            (data["CIIM"] - data["CIIM"].min()) / (data["CIIM"].max() - data["CIIM"].min() + 1e-6)
        ) * 25 + 10
    else:
        data["marker_size"] = 15
    
    # Filter out rows without coordinates
    map_data = data.dropna(subset=["lat", "lon"]).copy()
    
    if not map_data.empty:
        # Create improved map with custom colors
        fig_map = px.scatter_map(
            map_data,
            lat="lat",
            lon="lon",
            color="CIIM",
            size="marker_size",
            hover_name="district",
            hover_data={
                "CIIM": ":.2f",
                "biometric_intensity": ":.2f",
                "child_bio_ratio": ":.2f",
                "policy_flag": True
            } if "policy_flag" in map_data.columns else {
                "CIIM": ":.2f",
                "biometric_intensity": ":.2f",
                "child_bio_ratio": ":.2f"
            },
            zoom=4.2,
            map_style="carto-positron",
            color_continuous_scale=[(0, "green"), (0.5, "yellow"), (1, "red")],
            labels={"CIIM": "Risk Score (0-100)"},
            title="Aadhaar Identity Access Risk Map - District Level Analysis"
        )
        
        fig_map.update_layout(
            height=600,
            margin=dict(l=0, r=0, t=40, b=0),
            coloraxis_colorbar=dict(
                title="CIIM Risk Score",
                tickmode="linear",
                tick0=0,
                dtick=0.2
            )
        )
        
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("⚠️ No geographic data available for mapping.")
else:
    st.error("CIIM column not found in data.")

st.markdown("---")
st.markdown("## 📍 District-Level Deep Dive Analysis")

# District selector with improved UI
districts_available = sorted(data["district"].dropna().unique())
if districts_available:
    col_sel1, col_sel2 = st.columns([3, 1])
    
    with col_sel1:
        district = st.selectbox(
            "🔍 Select District for Detailed Analysis",
            districts_available,
            help="Choose a district to view comprehensive risk analysis and recommendations"
        )
    
    with col_sel2:
        # Show district count
        st.metric("Available Districts", len(districts_available))
    
    row = data[data["district"] == district].iloc[0]
else:
    st.error("No districts available in current selection.")
    st.stop()

# District info header
st.markdown(f"### 🏛️ **{district}**")
if "state" in row:
    st.caption(f"State: {row['state']} | Assessment Date: {selected_date}")

# Create tabs for better organization
tab1, tab2, tab3, tab4 = st.tabs(["⏳ Risk Forecast", "👥 Human Impact", "📊 Risk Drivers", "🛠️ Recommendations"])

with tab1:
    st.markdown("### ⏳ Time Until High-Risk Conditions")
    st.caption("Estimated time before district reaches critical risk levels (based on current trends)")

    # Get TTF from data if available, otherwise calculate
    ttf = float(row.get("TTF", 0))
    biometric_intensity = float(row.get("biometric_intensity", 0))
    bio_growth = float(row.get("bio_growth", 0))
    growth_direction = row.get("growth_direction", "STABLE")

    # If TTF not in data, calculate it (should be calculated in feature builder)
    if ttf == 0:
        BASE_TIME = 12
        growth_factor = 1 + max(0, bio_growth)  # Only positive growth accelerates
        intensity_weighted = biometric_intensity * growth_factor
        ttf = BASE_TIME / (intensity_weighted + 1e-3)
        if biometric_intensity < 0.2:
            ttf = ttf * 1.5
        ttf = min(max(ttf, 1), 24)

    # Visual TTF display with gauge chart
    col_ttf1, col_ttf2 = st.columns([2, 1])
    
    with col_ttf1:
        # Create gauge chart for TTF
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = ttf,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Time Until High-Risk (Months)"},
            delta = {'reference': 12, 'position': "top"},
            gauge = {
                'axis': {'range': [None, 24], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "darkblue"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 6], 'color': 'red'},
                    {'range': [6, 12], 'color': 'orange'},
                    {'range': [12, 18], 'color': 'yellow'},
                    {'range': [18, 24], 'color': 'green'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 6
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_ttf2:
        # Interpret TTF for policy-makers
        if ttf >= 18:
            urgency_level = "🟢 Low"
            urgency_color = "green"
            ttf_interpretation = "District has adequate time to implement preventive measures"
        elif ttf >= 12:
            urgency_level = "🟡 Moderate"
            urgency_color = "yellow"
            ttf_interpretation = "Monitor trends and prepare intervention plans"
        elif ttf >= 6:
            urgency_level = "🟠 High"
            urgency_color = "orange"
            ttf_interpretation = "Intervention needed within 6 months"
        else:
            urgency_level = "🔴 Critical"
            urgency_color = "red"
            ttf_interpretation = "Immediate intervention required"

        st.markdown(f"### {urgency_level}")
        st.markdown(f"**Urgency Level:** {urgency_level}")
        st.write(ttf_interpretation)

    # Growth direction context with visual indicator
    st.markdown("---")
    if growth_direction == "INCREASING":
        st.error("⚠️ **Risk Trend: INCREASING** - Dependency on biometrics is growing. Immediate attention needed.")
    elif growth_direction == "DECREASING":
        st.success("✅ **Risk Trend: DECREASING** - District is moving toward safer enrollment patterns. Continue monitoring.")
    else:
        st.info("➡️ **Risk Trend: STABLE** - No significant change in biometric dependency. Maintain current measures.")

with tab2:
    # ----------------------------------------------------
    # HUMAN IMPACT (IMPROVED) - TAB 2
    # ----------------------------------------------------
    st.markdown("### 👥 People Potentially Affected")
    st.caption("Estimated number of citizens and children who may lose Aadhaar access if biometric systems fail")

    total_enrolled = float(row.get("total_enrolled", 0))
    child_ratio = float(row.get("child_bio_ratio", 0))

    citizens_at_risk = total_enrolled * biometric_intensity if total_enrolled > 0 else 0
    children_at_risk = citizens_at_risk * child_ratio if citizens_at_risk > 0 else 0
    adults_at_risk = citizens_at_risk - children_at_risk

    if citizens_at_risk > 0:
        # Display metrics in columns
        col_impact1, col_impact2, col_impact3 = st.columns(3)
        
        with col_impact1:
            st.metric(
                label="👥 Total Citizens at Risk",
                value=f"{int(citizens_at_risk):,}",
                help="Number of enrolled citizens who rely primarily on biometric authentication"
            )
        
        with col_impact2:
            st.metric(
                label="👶 Children at Special Risk",
                value=f"{int(children_at_risk):,}",
                help="Number of children (ages 5-17) using biometrics. Children's fingerprints change as they grow, making biometrics less reliable."
            )
        
        with col_impact3:
            st.metric(
                label="👤 Adults at Risk",
                value=f"{int(adults_at_risk):,}",
                help="Number of adult citizens dependent on biometric authentication"
            )
        
        # Visual representation with pie chart
        if children_at_risk > 0 or adults_at_risk > 0:
            fig_pie = go.Figure(data=[
                go.Pie(
                    labels=['Children at Risk', 'Adults at Risk'],
                    values=[children_at_risk, adults_at_risk],
                    hole=0.4,
                    marker_colors=['#ff9999', '#66b3ff'],
                    textinfo='label+percent+value',
                    texttemplate='%{label}<br>%{value:,.0f}<br>(%{percent})'
                )
            ])
            fig_pie.update_layout(
                title="Risk Distribution by Age Group",
                height=400,
                showlegend=True
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Percentage breakdown
        st.markdown("#### 📊 Risk Breakdown")
        col_pct1, col_pct2 = st.columns(2)
        with col_pct1:
            pct_citizens = (citizens_at_risk / total_enrolled * 100) if total_enrolled > 0 else 0
            st.progress(pct_citizens / 100)
            st.caption(f"**{pct_citizens:.1f}%** of enrolled citizens are at risk")
        with col_pct2:
            pct_children = (children_at_risk / citizens_at_risk * 100) if citizens_at_risk > 0 else 0
            st.progress(pct_children / 100)
            st.caption(f"**{pct_children:.1f}%** of at-risk citizens are children")
    else:
        st.info("ℹ️ No reliable population data available for this district")

with tab3:
    # ----------------------------------------------------
    # RISK DRIVERS AND POLICY STATUS - TAB 3
    # ----------------------------------------------------
    st.markdown("### 🧠 District Risk Analysis & Drivers")
    st.caption("Detailed breakdown of risk indicators and contributing factors")

    # Get policy flag from data (priority-based, calculated in feature builder)
    policy_flag = row.get("policy_flag", "NORMAL")
    ciim = float(row.get("CIIM", 0))
    child_ratio = float(row.get("child_bio_ratio", 0))
    bio_growth = float(row.get("bio_growth", 0))
    data_quality = row.get("data_quality_flag", "OK")
    biometric_intensity = float(row.get("biometric_intensity", 0))
    growth_direction = row.get("growth_direction", "STABLE")

    # Map flags to user-friendly descriptions
    flag_descriptions = {
    "EMERGENCY": {
        "icon": "🔴",
        "label": "Emergency Intervention Required",
        "description": "Critical risk level (CIIM > 0.7). Immediate UIDAI and State Government action needed.",
        "color": "error"
    },
    "PROTECT_CHILDREN": {
        "icon": "🟠",
        "label": "Protect Children Priority",
        "description": "High child biometric dependency (>10%). Enable non-biometric alternatives for children.",
        "color": "warning"
    },
    "AUDIT_EXPANSION": {
        "icon": "🟡",
        "label": "Audit Rapid Expansion",
        "description": "Rapid biometric growth (>30% in 3 months). Review enrollment practices and device quality.",
        "color": "warning"
    },
    "DATA_REVIEW": {
        "icon": "⚪",
        "label": "Data Quality Review Needed",
        "description": "Suspicious data patterns detected. Verify enrollment data accuracy.",
        "color": "info"
    },
    "NORMAL": {
        "icon": "🟢",
        "label": "Normal Operations",
        "description": "Risk levels within acceptable range. Continue routine monitoring.",
        "color": "success"
    }
}

    flag_info = flag_descriptions.get(policy_flag, flag_descriptions["NORMAL"])

    # Policy status display
    col_policy1, col_policy2 = st.columns([2, 1])
    with col_policy1:
        st.markdown(f"### {flag_info['icon']} Policy Action Status: {flag_info['label']}")
        st.write(flag_info['description'])
    with col_policy2:
        if data_quality != "OK":
            st.warning(f"⚠️ Data Quality: {data_quality}")

    st.markdown("---")

    # Risk level with context
    if ciim > 0.7:
        risk_level = "🔴 CRITICAL"
        risk_desc = "District faces severe risk of identity access failures"
    elif ciim > 0.5:
        risk_level = "🟠 HIGH"
        risk_desc = "District requires attention and preventive measures"
    elif ciim > 0.3:
        risk_level = "🟡 MEDIUM"
        risk_desc = "District should be monitored regularly"
    else:
        risk_level = "🟢 LOW"
        risk_desc = "District has manageable risk levels"

    st.markdown(f"### Overall Risk Level: {risk_level}")
    st.caption(risk_desc)

    st.markdown("---")
    st.markdown("#### 📊 Risk Drivers (Contributing Factors)")

    # Display metrics in columns for better layout
    col_driver1, col_driver2 = st.columns(2)
    
    with col_driver1:
        st.metric(
            label="Citizens Dependent on Biometrics",
            value=f"{biometric_intensity*100:.1f}%",
            help="Percentage of enrolled citizens who rely primarily on biometric authentication. Higher values mean more people lose access if biometrics fail."
        )
        
        st.metric(
            label="Children Using Biometrics",
            value=f"{child_ratio*100:.1f}%",
            help="Percentage of biometric users who are children (ages 5-17). Children's fingerprints change as they grow, making biometrics less reliable for them."
        )
    
    with col_driver2:
        # Growth - with direction
        growth_pct = bio_growth * 100
        if growth_direction == "INCREASING":
            growth_help = f"Biometric dependency is increasing at {growth_pct:.1f}% per month. This signals growing reliance on biometrics."
        elif growth_direction == "DECREASING":
            growth_help = f"Biometric dependency is decreasing at {abs(growth_pct):.1f}% per month. This is positive - district is moving toward safer patterns."
        else:
            growth_help = "Biometric dependency is stable. No significant change detected."

        st.metric(
            label="Biometric Dependency Trend",
            value=f"{growth_pct:+.1f}%",
            help=growth_help
        )
        
        # CIIM score with interpretation
        ciim_pct = ciim * 100
        st.metric(
            label="CIIM Score (Composite Risk)",
            value=f"{ciim_pct:.1f}/100",
            help="Combined risk score (0-100) combining biometric intensity, growth trends, and child exclusion risk. Higher scores indicate greater vulnerability."
        )

    # Visual representation with bar chart
    st.markdown("---")
    risk_components = {
        'Biometric Intensity (50%)': biometric_intensity * 0.5,
        'Growth Penalty (30%)': max(0, bio_growth) * 0.3,
        'Exclusion Risk (20%)': (child_ratio * biometric_intensity) * 0.2
    }
    
    fig_components = go.Figure(data=[
        go.Bar(
            x=list(risk_components.keys()),
            y=list(risk_components.values()),
            marker_color=['#ff6b6b', '#ffd93d', '#6bcf7f'],
            text=[f'{v*100:.1f}%' for v in risk_components.values()],
            textposition='auto'
        )
    ])
    fig_components.update_layout(
        title="CIIM Score Breakdown (Component Contribution)",
        yaxis_title="Contribution to CIIM",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_components, use_container_width=True)

with tab4:
    # ----------------------------------------------------
    # ACTIONABLE RECOMMENDATIONS - TAB 4
    # ----------------------------------------------------
    st.markdown("### 🛠 Recommended Preventive Actions")
    st.caption("Evidence-based interventions to reduce identity access risks")

    biometric_intensity = float(row.get("biometric_intensity", 0))
    child_ratio = float(row.get("child_bio_ratio", 0))
    bio_growth = float(row.get("bio_growth", 0))
    ciim = float(row.get("CIIM", 0))
    growth_direction = row.get("growth_direction", "STABLE")

    recommendations = []

    # 🔴 CRITICAL RISK
    if ciim > 0.6:
        recommendations.append({
            "priority": "🔴 HIGH",
            "action": "Immediate UIDAI and State Government coordination",
            "details": (
                "District faces critical Aadhaar access risk. "
                "Immediate coordination required for technical, policy, and field-level intervention."
            )
        })

    # 👶 CHILD PROTECTION
    if child_ratio > 0.3:
        recommendations.append({
            "priority": "🟠 HIGH",
            "action": "Enable non-biometric Aadhaar options for children",
            "details": (
                f"{child_ratio*100:.1f}% of biometric users are children. "
                "Enable OTP-based authentication, face authentication, and assisted modes."
            )
        })

    # 🧾 BIOMETRIC DEPENDENCY
    if biometric_intensity > 0.6:
        recommendations.append({
            "priority": "🟠 HIGH",
            "action": "Expand assisted Aadhaar centers and offline KYC",
            "details": (
                f"{biometric_intensity*100:.1f}% of citizens depend on biometrics. "
                "Increase assisted centers and offline authentication facilities."
            )
        })

    # 📈 RAPID EXPANSION
    if bio_growth > 0.05 and growth_direction == "INCREASING":
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "action": "Audit biometric expansion and enrollment practices",
            "details": (
                f"Biometric dependency growing at {bio_growth*100:.1f}% per month. "
                "Audit devices, operators, and fallback availability."
            )
        })

    # ✅ DEFAULT SAFE STATE
    if not recommendations:
        recommendations.append({
            "priority": "🟢 MONITOR",
            "action": "Continue routine monitoring",
            "details": (
                "Risk indicators are within acceptable limits. "
                "Maintain preventive measures and periodic audits."
            )
        })

    # DISPLAY RECOMMENDATIONS
    for i, rec in enumerate(recommendations, 1):
        with st.expander(
            f"{rec['priority']} Priority #{i}: {rec['action']}",
            expanded=(i == 1 and rec['priority'] != "🟢 MONITOR")
        ):
            st.write(rec["details"])
