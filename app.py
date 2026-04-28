import streamlit as st
import pandas as pd
import numpy as np
import io
from growth_analysis import (fit_growth_curve, detect_phases,
    calc_doubling_time, build_plotly_figure)
from ai_reporter import generate_interpretation, generate_discussion_points

st.set_page_config(page_title="Growth Curve Analyser",
                   page_icon="🦠", layout="wide")
st.title("🦠 Bacterial Growth Curve Analyser")
st.markdown("*Upload OD₆₀₀ data → detect growth phases → AI writes your Results section*")

# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Experiment details")
    organism = st.text_input("Organism name",
        placeholder="e.g. Azospirillum brasilense NFB-01")
    medium   = st.text_input("Growth medium", value="Nutrient broth")
    temp     = st.number_input("Temperature (°C)", value=30.0, step=0.5)

    st.divider()
    st.markdown("### 📂 File format guide")
    st.markdown("""
**Excel (.xlsx) — recommended**
- One file, one sheet per species
- Each sheet needs two columns:
  `time_hours` and `OD600`
- Sheet name = organism name

**CSV (.csv)**
- Single sheet only
- Same two columns required
""")

    # Sample Excel download
    st.divider()
    st.markdown("**Download a sample Excel template:**")

    # Build a sample Excel file in memory with 2 example sheets
    sample_buf = io.BytesIO()
    with pd.ExcelWriter(sample_buf, engine="openpyxl") as writer:
        pd.DataFrame({
            "time_hours": [0,2,4,6,8,10,12,14,16,18,20,22,24],
            "OD600":      [0.05,0.055,0.062,0.078,0.11,0.19,
                           0.38,0.71,1.09,1.45,1.68,1.79,1.84]
        }).to_excel(writer, sheet_name="Azospirillum brasilense", index=False)

        pd.DataFrame({
            "time_hours": [0,2,4,6,8,10,12,14,16,18,20,22,24],
            "OD600":      [0.04,0.048,0.058,0.072,0.10,0.17,
                           0.33,0.65,1.01,1.38,1.60,1.72,1.78]
        }).to_excel(writer, sheet_name="Cupriavidus sp.", index=False)

    st.download_button(
        "⬇ Download sample Excel template",
        data=sample_buf.getvalue(),
        file_name="growth_curve_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ── File upload ──────────────────────────────────────────────────────────
st.markdown("### 📤 Upload your data")

file_type = st.radio("File type", ["Excel (.xlsx)", "CSV (.csv)"],
                      horizontal=True)

uploaded = st.file_uploader(
    "Upload file",
    type=["xlsx", "csv"],
    help="Excel: multiple sheets supported. CSV: single sheet only."
)

df = None
selected_sheet = None

if uploaded:
    # ── Excel: show sheet selector ────────────────────────────────────────
    if file_type == "Excel (.xlsx)":
        try:
            xl = pd.ExcelFile(uploaded)
            sheet_names = xl.sheet_names

            if len(sheet_names) == 0:
                st.error("This Excel file has no sheets.")
                st.stop()

            st.markdown("### 🧫 Select bacterial species (sheet)")
            st.caption(f"Found **{len(sheet_names)}** sheet(s) in this file")

            # Show sheets as selectable cards in columns
            cols = st.columns(min(len(sheet_names), 4))
            for i, name in enumerate(sheet_names):
                with cols[i % 4]:
                    st.markdown(f"""
                    <div style="
                        background:var(--background-color,#f8f9fa);
                        border:1px solid #dee2e6;
                        border-radius:8px;
                        padding:10px;
                        text-align:center;
                        font-size:13px;
                        margin-bottom:8px">
                        🦠 {name}
                    </div>""", unsafe_allow_html=True)

            selected_sheet = st.selectbox(
                "Choose which species to analyse:",
                options=sheet_names,
                help="Each sheet = one bacterial species"
            )

            df = xl.parse(selected_sheet)

            # Auto-fill organism name from sheet name if left blank
            if not organism and selected_sheet:
                organism = selected_sheet

            st.success(f"✅ Loaded sheet: **{selected_sheet}** "
                       f"({len(df)} rows)")

        except Exception as e:
            st.error(f"Could not read Excel file: {e}")
            st.stop()

    # ── CSV: read directly ────────────────────────────────────────────────
    else:
        try:
            df = pd.read_csv(uploaded)
            st.success(f"✅ Loaded CSV ({len(df)} rows)")
        except Exception as e:
            st.error(f"Could not read CSV file: {e}")
            st.stop()

# ── Validate columns ──────────────────────────────────────────────────────
if df is not None:
    df.columns = df.columns.str.strip()  # remove accidental spaces

    if "time_hours" not in df.columns or "OD600" not in df.columns:
        st.error("❌ The selected sheet must have columns named exactly: "
                 "`time_hours` and `OD600`")
        st.markdown("Your columns: " + ", ".join([f"`{c}`" for c in df.columns]))
        st.stop()

    # Drop any rows with missing values
    df = df[["time_hours", "OD600"]].dropna()

    if len(df) < 6:
        st.warning("⚠ At least 6 data points are recommended for a reliable "
                   "Gompertz fit. Add more time points if possible.")

    time  = df["time_hours"].values.astype(float)
    od600 = df["OD600"].values.astype(float)

    # Show raw data preview in expander
    with st.expander("👁 Preview raw data"):
        col_prev1, col_prev2 = st.columns([1, 2])
        with col_prev1:
            st.dataframe(df, use_container_width=True, height=250)
        with col_prev2:
            import plotly.graph_objects as go
            fig_raw = go.Figure()
            fig_raw.add_trace(go.Scatter(
                x=time, y=od600, mode="lines+markers",
                line=dict(color="#1D9E75"), marker=dict(size=7)
            ))
            fig_raw.update_layout(
                title="Raw data preview",
                xaxis_title="Time (hours)", yaxis_title="OD₆₀₀",
                height=230, margin=dict(l=40,r=20,t=40,b=40),
                plot_bgcolor="white"
            )
            fig_raw.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
            fig_raw.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
            st.plotly_chart(fig_raw, use_container_width=True)

    # ── Curve fitting ─────────────────────────────────────────────────────
    st.markdown("### 📊 Growth curve analysis")
    with st.spinner("Fitting Gompertz model..."):
        params = fit_growth_curve(time, od600)

    if not params["success"]:
        st.error(f"Curve fitting failed: {params['error']}\n\n"
                 "Try adding more data points, especially in the lag and "
                 "stationary phases.")
        st.stop()

    phases   = detect_phases(time, od600, params)
    doubling = calc_doubling_time(params["mu_max"])

    col1, col2 = st.columns([3, 1])
    with col1:
        fig = build_plotly_figure(time, od600, params, phases,
                                   organism or "Bacterial isolate")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.metric("μmax",           f"{params['mu_max']:.4f} h⁻¹")
        st.metric("Doubling time",  f"{doubling} hours")
        st.metric("Lag phase ends", f"{phases['lag_end']} hours")
        st.metric("Log phase",      f"{phases['log_start']}–{phases['log_end']} h")
        st.metric("Max OD₆₀₀",     f"{max(od600):.3f}")

        # Download chart data as CSV
        result_df = pd.DataFrame({"time_hours": time, "OD600": od600})
        st.download_button("⬇ Download data as CSV",
            result_df.to_csv(index=False),
            f"{organism or 'data'}_growth.csv", "text/csv")

    # ── AI interpretation ─────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🤖 AI-Generated Results Section")

    if not organism:
        st.info("💡 Tip: Enter the organism name in the sidebar for a more "
                "specific AI interpretation.")

    if st.button("✨ Generate Results paragraph", type="primary",
                 use_container_width=True):
        with st.spinner("Claude is writing your Results section..."):
            try:
                result  = generate_interpretation(
                    organism=organism or "the bacterial isolate",
                    mu_max=params["mu_max"],
                    doubling_time=doubling,
                    lag_hours=phases["lag_end"],
                    log_end_hours=phases["log_end"],
                    max_od=max(od600),
                    medium=medium,
                    temp_c=temp
                )
                discuss = generate_discussion_points(
                    params["mu_max"], doubling, phases["lag_end"]
                )
                st.success("Results paragraph — ready to paste into your thesis")
                st.markdown(f"> {result}")
                st.download_button("📋 Save Results as .txt",
                    result, f"{organism or 'results'}_paragraph.txt")
                with st.expander("💡 Discussion section hints"):
                    st.markdown(discuss)

            except Exception as e:
                st.error(f"AI generation failed: {e}\n\n"
                         "Check that your API key is correct in Streamlit Secrets.")

    # ── Multi-sheet comparison note ───────────────────────────────────────
    if file_type == "Excel (.xlsx)" and len(xl.sheet_names) > 1:
        st.divider()
        st.info(f"📋 Your file has **{len(xl.sheet_names)} species sheets**. "
                f"Use the dropdown above to switch between them and analyse "
                f"each one separately. Each analysis is independent.")

else:
    st.info("👈 Upload an Excel or CSV file above to begin")