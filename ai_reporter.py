import anthropic, os
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

# Works locally (reads .env) AND on Streamlit Cloud (reads st.secrets)
api_key = st.secrets.get("ANTHROPIC_API_KEY") if hasattr(st, "secrets") else None
if not api_key:
    api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)

SYSTEM = """You are a scientific writing assistant in microbiology.
Write concise publication-ready Results paragraphs in formal academic
English, third-person passive voice, 80-120 words, no bullet points."""

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
        model="claude-sonnet-4-20250514", max_tokens=300,
        system=SYSTEM, messages=[{"role":"user","content":prompt}]
    )
    return msg.content[0].text

def generate_discussion_points(mu_max, doubling_time, lag_hours):
    prompt = f"""Given μmax={mu_max:.3f} h⁻¹, doubling={doubling_time:.2f}h,
lag={lag_hours:.2f}h — give 3 bullet points for a Discussion section.
One sentence each. Start each with a dash (-)."""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=200,
        messages=[{"role":"user","content":prompt}]
    )
    return msg.content[0].text