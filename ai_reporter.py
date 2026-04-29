import anthropic, os
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

api_key = st.secrets.get("ANTHROPIC_API_KEY") if hasattr(st, "secrets") else None
if not api_key:
    api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)

MODEL = "claude-sonnet-4-6"

SYSTEM_TEXT = """You are a scientific writing assistant in microbiology.
Write concise publication-ready Results paragraphs in formal academic
English, third-person passive voice, 80-120 words, no bullet points."""

# Cached system block — reused across all calls so Anthropic only processes it once
SYSTEM_BLOCK = [{"type": "text", "text": SYSTEM_TEXT,
                 "cache_control": {"type": "ephemeral"}}]


def generate_interpretation(organism, mu_max, doubling_time,
                             lag_hours, log_end_hours, max_od,
                             medium="nutrient broth", temp_c=30.0):
    prompt = f"""Write a Results paragraph for this growth data:
Organism: {organism}
Medium: {medium}, Temperature: {temp_c}°C
μmax: {mu_max:.4f} h⁻¹, Doubling time: {doubling_time:.2f} h
Lag phase: {lag_hours:.2f} h, Log phase ends: {log_end_hours:.2f} h
Max OD₆₀₀: {max_od:.3f}
Context: candidate nitrogen-fixing biofertilizer strain."""
    msg = client.messages.create(
        model=MODEL, max_tokens=300,
        system=SYSTEM_BLOCK,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


def generate_discussion_points(mu_max, doubling_time, lag_hours):
    prompt = f"""Given μmax={mu_max:.3f} h⁻¹, doubling={doubling_time:.2f}h,
lag={lag_hours:.2f}h — give 3 bullet points for a Discussion section.
One sentence each. Start each with a dash (-)."""
    msg = client.messages.create(
        model=MODEL, max_tokens=200,
        system=SYSTEM_BLOCK,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


def generate_standard_curve_results(assay_name, model_type, equation, r_squared,
                                     conc_min, conc_max, x_unit,
                                     abso_min, abso_max, y_unit,
                                     n_points, unknowns_summary=""):
    parts = [
        f"Assay: {assay_name}",
        f"Model: {model_type}, Equation: {equation}, R²: {r_squared:.4f}",
        f"Concentration range: {conc_min:.2f}–{conc_max:.2f} {x_unit}",
        f"Absorbance range: {abso_min:.4f}–{abso_max:.4f} {y_unit}",
        f"Standard points: {n_points}",
    ]
    if unknowns_summary:
        parts.append(f"Unknown samples:\n{unknowns_summary}")
    prompt = ("Write a Results paragraph for a standard curve:\n\n"
              + "\n".join(parts)
              + "\n\nThird-person passive voice, 80–120 words, academic microbiology style. "
                "Include equation, R² value, and concentration range.")
    msg = client.messages.create(
        model=MODEL, max_tokens=300,
        system=SYSTEM_BLOCK,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text
