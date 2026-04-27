import streamlit as st
import pandas as pd
import numpy as np
from growth_analysis import (fit_growth_curve, detect_phases,
    calc_doubling_time, build_plotly_figure)
from ai_reporter import generate_interpretation, generate_discussion_points

st.set_page_config(page_title="Growth Curve Analyser",
                   page_icon="🦠", layout="wide")
st.title("🦠 Bacterial Growth Curve Analyser")
st.markdown("*Upload OD₆₀₀ data → detect growth phases → AI writes your Results section*")

with st.sidebar:
    st.header("Experiment details")
    organism = st.text_input("Organism name",
        placeholder="e.g. Azospirillum brasilense NFB-01")
    medium   = st.text_input("Growth medium", value="Nutrient broth")
    temp     = st.number_input("Temperature (°C)", value=30.0, step=0.5)
    st.divider()
    st.markdown("**CSV format:** two columns — `time_hours` and `OD600`")
    sample = pd.DataFrame({
        "time_hours":[0,4,8,12,16,20,24],
        "OD600":[0.05,0.08,0.28,0.98,1.71,1.87,1.89]
    })
    st.download_button("⬇ Download sample CSV",
        sample.to_csv(index=False),"sample_data.csv","text/csv")

uploaded = st.file_uploader("Upload your growth data (CSV)",
    type="csv", help="Must have columns: time_hours, OD600")

if uploaded:
    df = pd.read_csv(uploaded)
    if "time_hours" not in df.columns or "OD600" not in df.columns:
        st.error("CSV must have columns named 'time_hours' and 'OD600'")
        st.stop()
    time  = df["time_hours"].values
    od600 = df["OD600"].values

    with st.spinner("Fitting Gompertz model..."):
        params = fit_growth_curve(time, od600)

    if not params["success"]:
        st.error(f"Fitting failed: {params['error']}")
        st.stop()

    phases   = detect_phases(time, od600, params)
    doubling = calc_doubling_time(params["mu_max"])

    col1, col2 = st.columns([3,1])
    with col1:
        fig = build_plotly_figure(time, od600, params, phases,
                                   organism or "Bacterial isolate")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.metric("μmax",          f"{params['mu_max']:.4f} h⁻¹")
        st.metric("Doubling time", f"{doubling} hours")
        st.metric("Lag phase",     f"{phases['lag_end']} hours")
        st.metric("Max OD₆₀₀",    f"{max(od600):.3f}")

    st.divider()
    st.subheader("🤖 AI-Generated Results Section")
    if st.button("Generate Results paragraph", type="primary"):
        with st.spinner("Claude is writing your Results paragraph..."):
            result = generate_interpretation(
                organism=organism or "the bacterial isolate",
                mu_max=params["mu_max"], doubling_time=doubling,
                lag_hours=phases["lag_end"], log_end_hours=phases["log_end"],
                max_od=max(od600), medium=medium, temp_c=temp
            )
            discuss = generate_discussion_points(
                params["mu_max"], doubling, phases["lag_end"])
        st.success("Results paragraph — ready to paste into your thesis")
        st.markdown(f"> {result}")
        st.download_button("📋 Save as .txt", result, "results_paragraph.txt")
        with st.expander("💡 Discussion section hints"):
            st.markdown(discuss)
else:
    st.info("👈 Upload a CSV file using the button above to begin")