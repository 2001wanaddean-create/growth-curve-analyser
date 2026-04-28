import numpy as np
from scipy import stats
from scipy.optimize import curve_fit
import plotly.graph_objects as go
import pandas as pd

# ── Regression models ────────────────────────────────────────────────────

def linear_model(x, m, b):
    return m * x + b

def quadratic_model(x, a, b, c):
    return a * x**2 + b * x + c

def fit_standard_curve(concentrations, absorbances, model_type="linear"):
    """
    Fit a standard curve using linear or quadratic regression.
    Returns fit parameters, R², and the fitted function.
    """
    x = np.array(concentrations, dtype=float)
    y = np.array(absorbances, dtype=float)

    result = {"success": False, "model_type": model_type}

    try:
        if model_type == "linear":
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            result.update({
                "success":    True,
                "slope":      round(slope, 6),
                "intercept":  round(intercept, 6),
                "r_squared":  round(r_value**2, 6),
                "r_value":    round(r_value, 6),
                "p_value":    p_value,
                "std_err":    std_err,
                "equation":   f"y = {slope:.4f}x + {intercept:.4f}",
                "params":     (slope, intercept)
            })

        elif model_type == "quadratic":
            popt, pcov = curve_fit(quadratic_model, x, y)
            a, b, c = popt
            y_pred   = quadratic_model(x, *popt)
            ss_res   = np.sum((y - y_pred)**2)
            ss_tot   = np.sum((y - np.mean(y))**2)
            r2       = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            result.update({
                "success":   True,
                "a": round(a, 6), "b": round(b, 6), "c": round(c, 6),
                "r_squared": round(r2, 6),
                "equation":  f"y = {a:.4f}x² + {b:.4f}x + {c:.4f}",
                "params":    (a, b, c)
            })

    except Exception as e:
        result["error"] = str(e)

    return result


def calculate_unknown(absorbance_value, fit_result):
    """
    Back-calculate concentration from a measured absorbance value.
    Works for both linear and quadratic models.
    """
    y = float(absorbance_value)

    if fit_result["model_type"] == "linear":
        m, b = fit_result["params"]
        if m == 0:
            return None, "Slope is zero — cannot back-calculate"
        conc = (y - b) / m
        return round(conc, 4), None

    elif fit_result["model_type"] == "quadratic":
        a, b, c = fit_result["params"]
        # solve ax² + bx + (c - y) = 0
        discriminant = b**2 - 4*a*(c - y)
        if discriminant < 0:
            return None, "No real solution — absorbance out of range"
        x1 = (-b + np.sqrt(discriminant)) / (2*a)
        x2 = (-b - np.sqrt(discriminant)) / (2*a)
        # return the positive root
        candidates = [x for x in [x1, x2] if x >= 0]
        if not candidates:
            return None, "No positive concentration solution found"
        return round(min(candidates), 4), None


def build_standard_curve_figure(concentrations, absorbances,
                                  fit_result, assay_name,
                                  x_label, y_label,
                                  unknowns=None):
    """
    Build an interactive Plotly standard curve chart.
    unknowns: list of (absorbance, calculated_conc) tuples
    """
    x = np.array(concentrations, dtype=float)
    y = np.array(absorbances, dtype=float)

    x_smooth = np.linspace(min(x)*0.9, max(x)*1.1, 300)

    if fit_result["model_type"] == "linear":
        m, b = fit_result["params"]
        y_smooth = linear_model(x_smooth, m, b)
    else:
        a, b, c = fit_result["params"]
        y_smooth = quadratic_model(x_smooth, a, b, c)

    fig = go.Figure()

    # Fitted curve
    fig.add_trace(go.Scatter(
        x=x_smooth, y=y_smooth, mode="lines",
        name="Fitted curve",
        line=dict(color="#378ADD", width=2.5)
    ))

    # Standard data points
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers",
        name="Standards",
        marker=dict(size=10, color="#1D9E75",
                    line=dict(width=1.5, color="white"),
                    symbol="circle")
    ))

    # Unknown samples — plotted as dashed drop lines
    if unknowns:
        for i, (abs_val, conc_val) in enumerate(unknowns):
            if conc_val is not None:
                # Horizontal line from y-axis to curve
                fig.add_shape(type="line",
                    x0=min(x)*0.9, x1=conc_val,
                    y0=abs_val,    y1=abs_val,
                    line=dict(color="#BA7517", width=1.2, dash="dot"))
                # Vertical drop line
                fig.add_shape(type="line",
                    x0=conc_val, x1=conc_val,
                    y0=0,        y1=abs_val,
                    line=dict(color="#BA7517", width=1.2, dash="dot"))
                # Point on curve
                fig.add_trace(go.Scatter(
                    x=[conc_val], y=[abs_val], mode="markers",
                    name=f"Unknown {i+1}: {conc_val} ({abs_val} abs)",
                    marker=dict(size=11, color="#BA7517",
                                symbol="diamond",
                                line=dict(width=1.5, color="white"))
                ))

    r2 = fit_result.get("r_squared", 0)
    eq  = fit_result.get("equation", "")

    fig.update_layout(
        title=dict(
            text=f"Standard Curve — {assay_name}"
                 f"<br><sup>{eq} &nbsp;|&nbsp; R² = {r2:.6f}</sup>",
            font_size=15
        ),
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor="white",
        height=430,
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
        margin=dict(l=55, r=20, t=90, b=50)
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=True,
                     zerolinecolor="#e0e0e0")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=True,
                     zerolinecolor="#e0e0e0")
    return fig


def get_quality_assessment(r_squared, n_points, model_type):
    """
    Return a quality rating and advice based on R² value.
    """
    if r_squared >= 0.999:
        rating  = "Excellent"
        colour  = "success"
        message = ("R² ≥ 0.999 — publication-ready standard curve. "
                   "Your pipetting technique and reagent preparation are consistent.")
    elif r_squared >= 0.995:
        rating  = "Good"
        colour  = "success"
        message = ("R² ≥ 0.995 — acceptable for most research applications. "
                   "Minor variation likely from pipetting error.")
    elif r_squared >= 0.990:
        rating  = "Acceptable"
        colour  = "warning"
        message = ("R² ≥ 0.990 — usable but re-running the assay is recommended. "
                   "Check for outlier points and reagent freshness.")
    else:
        rating  = "Poor — re-run recommended"
        colour  = "error"
        message = ("R² < 0.990 — this curve should not be used for quantification. "
                   "Common causes: degraded reagent, wrong wavelength, "
                   "pipetting inconsistency, or sample interference.")

    if n_points < 5:
        message += " Note: fewer than 5 standard points reduces reliability — add more concentrations."

    return rating, colour, message