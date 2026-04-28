import numpy as np
from scipy import stats
import plotly.graph_objects as go

# ── Curve fitting ─────────────────────────────────────────────────────────

def fit_standard_curve(concentration, absorbance, model_type="linear"):
    try:
        x = np.array(concentration, dtype=float)
        y = np.array(absorbance, dtype=float)

        if model_type == "linear":
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            r_squared = r_value ** 2
            eq = (f"y = {slope:.4f}x + {intercept:.4f}"
                  if intercept >= 0
                  else f"y = {slope:.4f}x - {abs(intercept):.4f}")
            return {
                "success": True, "model": "linear",
                "params": {"slope": slope, "intercept": intercept},
                "r_squared": r_squared, "equation": eq,
                "std_err": std_err, "p_value": p_value
            }

        elif model_type == "polynomial":
            coeffs  = np.polyfit(x, y, 2)
            a, b, c = coeffs
            y_pred  = np.polyval(coeffs, x)
            ss_res  = np.sum((y - y_pred) ** 2)
            ss_tot  = np.sum((y - np.mean(y)) ** 2)
            r_sq    = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            sb = "+" if b >= 0 else "-"
            sc = "+" if c >= 0 else "-"
            eq = f"y = {a:.4f}x² {sb} {abs(b):.4f}x {sc} {abs(c):.4f}"
            return {
                "success": True, "model": "polynomial",
                "params": {"a": a, "b": b, "c": c},
                "r_squared": r_sq, "equation": eq
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def calculate_unknown(absorbance_value, fit_result):
    """Back-calculate concentration from absorbance."""
    try:
        y = float(absorbance_value)
        if fit_result["model"] == "linear":
            m = fit_result["params"]["slope"]
            b