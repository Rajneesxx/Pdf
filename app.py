import streamlit as st
import pdfplumber
import pandas as pd
import json
from openai import OpenAI

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="Payer Plan GPT Extractor", layout="wide")
st.title("🤖 Payer Plan Field Extractor with GPT (Enhanced)")

mode = st.radio("Choose Mode:", ["Single PDF Extraction", "Compare Two PDFs"])

# -------------------- Runtime OpenAI API Key --------------------
api_key_input = st.text_input("Enter OpenAI API Key:", type="password")
if not api_key_input:
    st.warning("Please enter your OpenAI API key to continue.")
    st.stop()

client = OpenAI(api_key=api_key_input)

# -------------------- Helper Functions --------------------
def pdf_to_text(pdf_file):
    """Extract text from uploaded PDF"""
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def clean_text(text):
    """Remove extra spaces and newlines"""
    return " ".join(text.split())

def extract_with_gpt(text, fields, client, max_retries=3):
    """
    Extract specified fields from policy text using OpenAI GPT.

    Args:
        text (str): The full policy text.
        fields (list[str]): List of field names to extract.
        client (OpenAI): OpenAI client instance.
        max_retries (int): Number of retries if JSON parsing fails.

    Returns:
        dict: Dictionary mapping field names to extracted values.
    """
    if client is None:
        return {f: "" for f in fields}

    # Strong structured prompt
    prompt = f"""
You are a strict data extraction assistant.
Extract ONLY the following fields from the insurance policy text.

Fields: {', '.join(fields)}

IMPORTANT:
- Return a single JSON object only.
- Keys must match the field names exactly.
- Do NOT add any explanation, notes, or extra text outside the JSON.
- If a field is missing, use an empty string as its value.

Policy Text:
{text}
"""

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            resp_text = resp.choices[0].message.content.strip()

            # Auto-cleaning: remove any text before/after JSON
            idx_start = resp_text.find("{")
            idx_end = resp_text.rfind("}")
            if idx_start == -1 or idx_end == -1 or idx_end <= idx_start:
                raise ValueError("No JSON object found in GPT response.")
            resp_text = resp_text[idx_start:idx_end + 1]

            return json.loads(resp_text)

        except Exception as e:
            # If last attempt, return empty fields
            if attempt == max_retries - 1:
                print(f"GPT returned invalid JSON. Returning empty fields. Error: {e}")
                return {f: "" for f in fields}
            # Otherwise, retry
            continue
def display_comparison_table(df):
    """Highlight differences in a comparison table"""
    def highlight_diff(row):
        return ['background-color: yellow' if row['Old Policy'] != row['New Policy'] else '' for _ in row]
    st.dataframe(df.style.apply(highlight_diff, axis=1))

# -------------------- Fields to Extract --------------------
fields_input = st.text_area(
    "Fields to extract (one per line):",
    "Policy No\nPeriod of Insurance\nPlan"
)
target_fields = [f.strip() for f in fields_input.split("\n") if f.strip()]

# -------------------- Main App Logic --------------------
if mode == "Single PDF Extraction":
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
    if pdf_file:
        text = clean_text(pdf_to_text(pdf_file))
        data = extract_with_gpt(text, target_fields, client)
        st.table(pd.DataFrame(data.items(), columns=["Field", "Value"]))

else:
    col1, col2 = st.columns(2)
    with col1:
        old_pdf = st.file_uploader("Old Policy PDF", type=["pdf"], key="old")
    with col2:
        new_pdf = st.file_uploader("New Policy PDF", type=["pdf"], key="new")

    if old_pdf and new_pdf:
        old_text = clean_text(pdf_to_text(old_pdf))
        new_text = clean_text(pdf_to_text(new_pdf))
        old_data = extract_with_gpt(old_text, target_fields, client)
        new_data = extract_with_gpt(new_text, target_fields, client)

        df = pd.DataFrame({
            "Field": target_fields,
            "Old Policy": [old_data.get(f, "") for f in target_fields],
            "New Policy": [new_data.get(f, "") for f in target_fields],
        })
        display_comparison_table(df)
