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

def extract_with_gpt(text, fields, client):
    """
    Extract specific fields from policy text using GPT
    """
    prompt = f"""
You are a data extraction assistant.
Extract ONLY the following fields from the insurance policy text.
Fields: {', '.join(fields)}

Return a valid JSON object with keys exactly matching the field names.
If a field is not found, set its value to an empty string.

Policy Text:
{text}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = resp.choices[0].message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            st.warning("GPT returned invalid JSON. Returning empty fields.")
            return {f: "" for f in fields}
    except Exception as e:
        st.error(f"Error calling GPT: {e}")
        return {f: "" for f in fields}

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
