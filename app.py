import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go

from growth_analysis import (fit_growth_curve, detect_phases,
    calc_doubling_time, build_plotly_figure, build_excel_growth_chart)
from ai_reporter import (generate_interpretation, generate_discussion_points,
    generate_standard_curve_results)
from standard_curve import (fit_standard_curve, calculate_unknown,
    build_standard_curve_figure, build_excel_standard_chart, ASSAY_PRESETS)

st.set_page_config(page_title="BioLab Analyser",
                   page_icon="🔬", layout="wide")

# ── Bacteria mascot SVG ──────────────────────────────────────────────────────
MASCOT_SVG = """
<div style="text-align:center; padding:4px 0 0 0;">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 160" width="88" height="140">
  <!-- flagellum -->
  <path d="M50,50 C67,32 33,18 56,4"
        stroke="#0e7a58" stroke-width="3.5" fill="none" stroke-linecap="round"/>
  <!-- left pilus -->
  <path d="M18,88 C4,73 2,57 9,46"
        stroke="#0e7a58" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <!-- right pilus -->
  <path d="M82,88 C96,73 98,57 91,46"
        stroke="#0e7a58" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <!-- body shadow -->
  <ellipse cx="52" cy="107" rx="36" ry="47" fill="#0e7a58" opacity="0.25"/>
  <!-- body -->
  <ellipse cx="50" cy="105" rx="36" ry="47" fill="#1D9E75"/>
  <!-- shine highlight -->
  <ellipse cx="37" cy="78" rx="11" ry="7" fill="rgba(255,255,255,0.22)"
           transform="rotate(-20,37,78)"/>
  <!-- left eye white -->
  <circle cx="36" cy="90" r="10" fill="white"/>
  <!-- right eye white -->
  <circle cx="64" cy="90" r="10" fill="white"/>
  <!-- left pupil -->
  <circle cx="38" cy="89" r="6" fill="#1a1a2e"/>
  <!-- right pupil -->
  <circle cx="66" cy="89" r="6" fill="#1a1a2e"/>
  <!-- eye shines -->
  <circle cx="41" cy="86" r="2.5" fill="white"/>
  <circle cx="69" cy="86" r="2.5" fill="white"/>
  <!-- blush left -->
  <ellipse cx="24" cy="100" rx="7" ry="4.5" fill="rgba(255,130,130,0.40)"/>
  <!-- blush right -->
  <ellipse cx="76" cy="100" rx="7" ry="4.5" fill="rgba(255,130,130,0.40)"/>
  <!-- smile -->
  <path d="M36,106 Q50,120 64,106"
        stroke="#1a1a2e" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <!-- membrane dots -->
  <circle cx="44" cy="128" r="4"   fill="rgba(255,255,255,0.14)"/>
  <circle cx="58" cy="136" r="3"   fill="rgba(255,255,255,0.14)"/>
  <circle cx="36" cy="133" r="2.5" fill="rgba(255,255,255,0.14)"/>
</svg>
<p style="font-size:10px;color:#888;margin:0;font-style:italic;">Azospirella</p>
</div>
"""

# ── Header ───────────────────────────────────────────────────────────────────
col_title, col_mascot = st.columns([7, 1])
with col_title:
    st.title("🔬 BioLab Analyser")
    st.markdown("*Bacterial growth curve analysis · Standard curve builder · AI-written Results*")
with col_mascot:
    st.markdown(MASCOT_SVG, unsafe_allow_html=True)

st.divider()

# ── Onboarding wizard ────────────────────────────────────────────────────────
STEPS = [
    ("👋 Welcome to BioLab Analyser!",
     "This tool helps you analyse **bacterial growth curves** and build "
     "**standard curves** — then writes a publication-ready Results section "
     "using Claude AI, ready to paste straight into your thesis.\n\n"
     "Click **Next →** for a 3-step quick-start guide, or **Skip** to jump right in."),
    ("🧫 Step 1 — Choose your analysis mode",
     "Use the radio buttons below the wizard to pick:\n\n"
     "- **📈 Growth Curve Analysis** — upload OD₆₀₀ vs time data, fit a Gompertz "
     "model, and extract μmax, doubling time, lag phase, and log phase automatically.\n"
     "- **📉 Standard Curve Builder** — Bradford, IAA, TAN assays (or custom). "
     "Enter standard points and calculate unknown sample concentrations."),
    ("📤 Step 2 — Upload or enter your data",
     "**Growth curve** — Excel or CSV with columns: `time_hours` and `OD600`\n\n"
     "**Standard curve** — columns: `concentration` and `absorbance`\n\n"
     "👉 Grab the **⬇ Sample Excel template** from the sidebar if you need a "
     "starter file. You can also type data directly into the table."),
    ("🤖 Step 3 — AI Results & Excel export",
     "After your analysis:\n\n"
     "- Click **✨ Generate Results paragraph** → Claude AI writes a formal "
     "Results section you can copy straight into your thesis.\n"
     "- Click **⬇ Download Excel chart** → get an editable `.xlsx` workbook "
     "with your raw data **and** an embedded chart you can style in Excel — "
     "no more screenshots!\n\nYou're all set. Happy analysing! 🎉"),
]

if "ob_done" not in st.session_state:
    st.session_state.ob_done = False
if "ob_step" not in st.session_state:
    st.session_state.ob_step = 0

if not st.session_state.ob_done:
    step = st.session_state.ob_step
    title, body = STEPS[step]
    n_steps = len(STEPS)

    with st.container(border=True):
        # Progress dots
        dots = "".join(
            "🟢 " if i == step else "⚪ "
            for i in range(n_steps)
        )
        st.caption(f"{dots}Step {step + 1} of {n_steps}")
        st.markdown(f"### {title}")
        st.markdown(body)

        c_back, c_next, c_skip = st.columns([1, 1, 5])
        with c_back:
            if step > 0:
                if st.button("← Back", key="ob_back"):
                    st.session_state.ob_step -= 1
                    st.rerun()
        with c_next:
            if step < n_steps - 1:
                if st.button("Next →", type="primary", key="ob_next"):
                    st.session_state.ob_step += 1
                    st.rerun()
            else:
                if st.button("🚀 Let's go!", type="primary", key="ob_done"):
                    st.session_state.ob_done = True
                    st.rerun()
        with c_skip:
            if st.button("Skip tutorial", key="ob_skip"):
                st.session_state.ob_done = True
                st.rerun()

    st.divider()

# ── Mode selector ─────────────────────────────────────────────────────────────
mode = st.radio(
    "**Select analysis mode:**",
    ["📈 Growth Curve Analysis", "📉 Standard Curve Builder"],
    horizontal=True
)
st.divider()

# ════════════════════════════════════════════════════════════════════════
# MODE 1 — GROWTH CURVE
# ════════════════════════════════════════════════════════════════════════
if mode == "📈 Growth Curve Analysis":

    with st.sidebar:
        st.header("⚗️ Experiment details")
        organism = st.text_input("Organism name",
            placeholder="e.g. Azospirillum brasilense NFB-01")
        medium = st.text_input("Growth medium", value="Nutrient broth")
        temp   = st.number_input("Temperature (°C)", value=30.0, step=0.5)
        st.divider()
        st.markdown("### 📂 File format")
        st.markdown("**Excel:** one file, one sheet per species.\n\nColumns: `time_hours`, `OD600`\n\n**CSV:** single sheet, same columns.")
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            pd.DataFrame({
                "time_hours":[0,2,4,6,8,10,12,14,16,18,20,22,24],
                "OD600":     [0.05,0.055,0.062,0.078,0.11,0.19,0.38,
                              0.71,1.09,1.45,1.68,1.79,1.84]
            }).to_excel(w, sheet_name="Azospirillum brasilense", index=False)
            pd.DataFrame({
                "time_hours":[0,2,4,6,8,10,12,14,16,18,20,22,24],
                "OD600":     [0.04,0.048,0.058,0.072,0.10,0.17,0.33,
                              0.65,1.01,1.38,1.60,1.72,1.78]
            }).to_excel(w, sheet_name="Cupriavidus sp.", index=False)
        st.download_button("⬇ Sample Excel template", buf.getvalue(),
            "growth_curve_template.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("### 📤 Upload growth data")
    ft  = st.radio("File type", ["Excel (.xlsx)","CSV (.csv)"],
                    horizontal=True, key="gc_ft")
    upl = st.file_uploader("Upload file", type=["xlsx","csv"], key="gc_up")
    df  = None

    if upl:
        if ft == "Excel (.xlsx)":
            try:
                xl   = pd.ExcelFile(upl)
                sn   = xl.sheet_names
                st.markdown("### 🧫 Select species (sheet)")
                st.caption(f"Found **{len(sn)}** sheet(s)")
                cols = st.columns(min(len(sn), 4))
                for i, n in enumerate(sn):
                    with cols[i % 4]:
                        st.markdown(
                            f'<div style="background:var(--background-color,#f8f9fa);'
                            f'border:1px solid #dee2e6;border-radius:8px;padding:10px;'
                            f'text-align:center;font-size:13px;margin-bottom:8px">'
                            f'🦠 {n}</div>', unsafe_allow_html=True)
                sel = st.selectbox("Choose species to analyse:", sn)
                df  = xl.parse(sel)
                if not organism:
                    organism = sel
                st.success(f"✅ Loaded: **{sel}** ({len(df)} rows)")
            except Exception as e:
                st.error(f"Could not read Excel: {e}"); st.stop()
        else:
            try:
                df = pd.read_csv(upl)
                st.success(f"✅ Loaded CSV ({len(df)} rows)")
            except Exception as e:
                st.error(f"Could not read CSV: {e}"); st.stop()

    if df is not None:
        df.columns = df.columns.str.strip()
        if "time_hours" not in df.columns or "OD600" not in df.columns:
            st.error("❌ Columns must be named `time_hours` and `OD600`")
            st.markdown("Your columns: " + ", ".join([f"`{c}`" for c in df.columns]))
            st.stop()
        df    = df[["time_hours","OD600"]].dropna()
        time  = df["time_hours"].values.astype(float)
        od600 = df["OD600"].values.astype(float)
        if len(df) < 6:
            st.warning("⚠ At least 6 data points recommended for Gompertz fit.")

        with st.expander("👁 Preview raw data"):
            c1, c2 = st.columns([1,2])
            with c1:
                st.dataframe(df, use_container_width=True, height=250)
            with c2:
                fr = go.Figure()
                fr.add_trace(go.Scatter(x=time, y=od600, mode="lines+markers",
                    line=dict(color="#1D9E75"), marker=dict(size=7)))
                fr.update_layout(title="Raw data", xaxis_title="Time (hours)",
                    yaxis_title="OD₆₀₀", height=230, plot_bgcolor="white",
                    margin=dict(l=40,r=20,t=40,b=40))
                fr.update_xaxes(showgrid=True,gridcolor="#f0f0f0")
                fr.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
                st.plotly_chart(fr, use_container_width=True)

        st.markdown("### 📊 Growth curve analysis")
        with st.spinner("Fitting Gompertz model..."):
            params = fit_growth_curve(time, od600)
        if not params["success"]:
            st.error(f"Fitting failed: {params['error']}"); st.stop()

        phases   = detect_phases(time, od600, params)
        doubling = calc_doubling_time(params["mu_max"])

        c1, c2 = st.columns([3,1])
        with c1:
            st.plotly_chart(
                build_plotly_figure(time, od600, params, phases,
                                    organism or "Bacterial isolate"),
                use_container_width=True)
        with c2:
            st.metric("μmax",           f"{params['mu_max']:.4f} h⁻¹")
            st.metric("Doubling time",  f"{doubling} hours")
            st.metric("Lag phase ends", f"{phases['lag_end']} hours")
            st.metric("Log phase",      f"{phases['log_start']}–{phases['log_end']} h")
            st.metric("Max OD₆₀₀",     f"{max(od600):.3f}")
            st.download_button("⬇ Download CSV", df.to_csv(index=False),
                f"{organism or 'data'}_growth.csv", "text/csv")

        # ── Excel chart download ──────────────────────────────────────────
        with st.spinner("Building Excel workbook..."):
            xl_bytes = build_excel_growth_chart(
                time, od600, params, organism or "Bacterial isolate")
        st.download_button(
            "📊 Download Excel chart (.xlsx)",
            xl_bytes,
            f"{organism or 'growth_curve'}_chart.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Editable Excel workbook with raw data, fitted curve, parameters, "
                 "and an embedded scatter chart you can style directly in Excel.",
            use_container_width=True,
        )

        st.divider()
        st.markdown("### 🤖 AI-Generated Results Section")
        if not organism:
            st.info("💡 Enter organism name in sidebar for a better interpretation.")
        if st.button("✨ Generate Results paragraph", type="primary",
                     use_container_width=True):
            with st.spinner("Claude is writing your Results section..."):
                try:
                    result  = generate_interpretation(
                        organism=organism or "the bacterial isolate",
                        mu_max=params["mu_max"], doubling_time=doubling,
                        lag_hours=phases["lag_end"],
                        log_end_hours=phases["log_end"],
                        max_od=max(od600), medium=medium, temp_c=temp)
                    discuss = generate_discussion_points(
                        params["mu_max"], doubling, phases["lag_end"])
                    st.success("Results paragraph — ready to paste into your thesis")
                    st.markdown(f"> {result}")
                    st.download_button("📋 Save as .txt", result,
                        f"{organism or 'results'}_paragraph.txt")
                    with st.expander("💡 Discussion hints"):
                        st.markdown(discuss)
                except Exception as e:
                    st.error(f"AI generation failed: {e}")
    else:
        st.info("👈 Upload a file above to begin")


# ════════════════════════════════════════════════════════════════════════
# MODE 2 — STANDARD CURVE
# ════════════════════════════════════════════════════════════════════════
else:

    with st.sidebar:
        st.header("📉 Standard curve settings")
        assay_choice = st.selectbox("Select assay type:",
                                     list(ASSAY_PRESETS.keys()))
        preset = ASSAY_PRESETS[assay_choice]
        st.info(f"**Wavelength:** {preset['wavelength']}\n\n{preset['description']}")
        st.divider()
        model_type = st.radio("Curve model:", ["linear","polynomial"],
            help="Linear for most colorimetric assays. Polynomial if curve saturates.")
        st.divider()
        x_unit = st.text_input("Concentration unit", value=preset["x_unit"]) \
                 if assay_choice == "Custom Assay" else preset["x_unit"]
        y_unit = st.text_input("Absorbance unit", value=preset["y_unit"]) \
                 if assay_choice == "Custom Assay" else preset["y_unit"]
        st.divider()
        st.download_button("⬇ Download sample data",
            pd.DataFrame(preset["sample_data"]).to_csv(index=False),
            f"{assay_choice.replace(' ','_')}_sample.csv", "text/csv")

    st.markdown(f"### 📤 Enter standard data — {assay_choice}")
    method = st.radio("Input method:", ["Upload CSV / Excel","Type in manually"],
                       horizontal=True)
    sc_df  = None

    if method == "Upload CSV / Excel":
        sc_ft  = st.radio("File type", ["Excel (.xlsx)","CSV (.csv)"],
                           horizontal=True, key="sc_ft")
        sc_upl = st.file_uploader("Upload file", type=["xlsx","csv"], key="sc_up",
            help="Columns needed: `concentration` and `absorbance`")
        if sc_upl:
            if sc_ft == "Excel (.xlsx)":
                xl_sc  = pd.ExcelFile(sc_upl)
                sc_sel = st.selectbox("Select sheet:", xl_sc.sheet_names)
                sc_df  = xl_sc.parse(sc_sel)
            else:
                sc_df = pd.read_csv(sc_upl)
    else:
        st.markdown("**Edit the table below** — add or remove rows as needed:")
        edited = st.data_editor(
            pd.DataFrame(preset["sample_data"]),
            num_rows="dynamic", use_container_width=True,
            column_config={
                "concentration": st.column_config.NumberColumn(
                    f"Concentration ({x_unit})", min_value=0.0, format="%.4f"),
                "absorbance": st.column_config.NumberColumn(
                    f"Absorbance ({y_unit})", min_value=0.0, format="%.4f")
            }, key="sc_edit")
        sc_df = edited

    if sc_df is not None:
        sc_df.columns = sc_df.columns.str.strip().str.lower()
        if "concentration" not in sc_df.columns or "absorbance" not in sc_df.columns:
            st.error("❌ Columns must be named `concentration` and `absorbance`")
            st.stop()
        sc_df = sc_df[["concentration","absorbance"]].dropna()
        if len(sc_df) < 3:
            st.warning("⚠ At least 3 standard points needed."); st.stop()

        conc = sc_df["concentration"].values.astype(float)
        abso = sc_df["absorbance"].values.astype(float)

        with st.spinner("Fitting standard curve..."):
            fit = fit_standard_curve(conc, abso, model_type)
        if not fit["success"]:
            st.error(f"Fitting failed: {fit['error']}"); st.stop()

        r2 = fit["r_squared"]
        r2_label = ("🟢 Excellent" if r2 >= 0.999 else
                    "🟡 Acceptable" if r2 >= 0.990 else
                    "🔴 Poor — check data")

        st.markdown("### 📊 Standard curve results")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("R²", f"{r2:.4f}")
        m2.metric("Quality", r2_label)
        m3.metric("Equation", fit["equation"])
        m4.metric("Model", fit["model"].capitalize())

        if r2 < 0.990:
            st.warning("⚠ R² below 0.990. Check for pipetting errors, wrong blank, "
                       "or try polynomial model.")
        elif r2 >= 0.999:
            st.success("✅ Excellent linearity — curve is publication-ready.")

        # ── Unknown calculator ───────────────────────────────────────────
        st.markdown("### 🧪 Calculate unknown sample concentrations")
        num_s = st.number_input("Number of unknown samples",
                                 min_value=1, max_value=20, value=3)
        unknowns = []
        ucols = st.columns(min(int(num_s), 4))
        for i in range(int(num_s)):
            with ucols[i % 4]:
                lbl = st.text_input(f"Sample {i+1} name",
                    value=f"Sample {i+1}", key=f"lbl_{i}")
                av  = st.number_input(f"Absorbance ({y_unit})",
                    min_value=0.0, value=0.5, step=0.001,
                    format="%.4f", key=f"av_{i}")
                cc  = calculate_unknown(av, fit)
                if cc is not None:
                    st.success(f"**{cc} {x_unit}**")
                else:
                    st.error("Out of range")
                unknowns.append({"label":lbl,"absorbance":av,"concentration":cc})

        # ── Chart ────────────────────────────────────────────────────────
        st.plotly_chart(
            build_standard_curve_figure(conc, abso, fit, assay_choice,
                                         x_unit, y_unit, unknowns),
            use_container_width=True)

        # ── Excel chart download ──────────────────────────────────────────
        with st.spinner("Building Excel workbook..."):
            xl_sc_bytes = build_excel_standard_chart(
                conc, abso, fit, assay_choice, x_unit, y_unit, unknowns)
        st.download_button(
            "📊 Download Excel chart (.xlsx)",
            xl_sc_bytes,
            f"{assay_choice.replace(' ','_')}_chart.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Editable Excel workbook with standard data, fitted curve, "
                 "unknown samples, and an embedded scatter chart.",
            use_container_width=True,
        )

        # ── Results table ────────────────────────────────────────────────
        st.markdown("### 📋 Results summary table")
        res_df = pd.DataFrame([{
            "Sample": r["label"],
            f"Absorbance ({y_unit})": r["absorbance"],
            f"Concentration ({x_unit})": (r["concentration"]
                                           if r["concentration"] is not None
                                           else "Out of range")
        } for r in unknowns])
        st.dataframe(res_df, use_container_width=True)
        st.download_button("⬇ Download results CSV",
            res_df.to_csv(index=False),
            f"{assay_choice.replace(' ','_')}_results.csv", "text/csv")

        # ── AI Results ───────────────────────────────────────────────────
        st.divider()
        st.markdown("### 🤖 AI-Generated Results Section")
        if st.button("✨ Generate Results paragraph", type="primary",
                     use_container_width=True, key="sc_ai"):
            with st.spinner("Claude is writing your Results section..."):
                try:
                    valid  = [r for r in unknowns if r["concentration"] is not None]
                    s_sum  = "\n".join([
                        f"{r['label']}: OD {r['absorbance']:.4f} → "
                        f"{r['concentration']} {x_unit}"
                        for r in valid]) if valid else ""
                    txt = generate_standard_curve_results(
                        assay_name=assay_choice,
                        model_type=fit["model"],
                        equation=fit["equation"],
                        r_squared=r2,
                        conc_min=float(min(conc)), conc_max=float(max(conc)),
                        x_unit=x_unit,
                        abso_min=float(min(abso)), abso_max=float(max(abso)),
                        y_unit=y_unit,
                        n_points=len(conc),
                        unknowns_summary=s_sum,
                    )
                    st.success("Results paragraph — ready to paste into your thesis")
                    st.markdown(f"> {txt}")
                    st.download_button("📋 Save as .txt", txt,
                        f"{assay_choice.replace(' ','_')}_paragraph.txt")
                except Exception as e:
                    st.error(f"AI generation failed: {e}")
    else:
        st.info("👆 Enter or upload your standard curve data above to begin")
