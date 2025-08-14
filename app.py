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

# -------------------- Predefined Fields --------------------
QLM_FIELDS = [
    "Insured", "Policy No", "Period of Insurance", "Plan",
    "For Eligible Medical Expenses at Al Ahli Hospital", "Inpatient Deductible",
    "Deductible per each outpatient consultation", "Vaccination of children",
    "Psychiatric Treatment", "Dental Copayment", "Maternity Copayment", "Optical Copayment"
]

ALKOOT_FIELDS = [
    "Policy Number", "Category", "Effective Date", "Expiry Date",
    "Provider-specific co-insurance at Al Ahli Hospital",
    "Co-insurance on all inpatient treatment", "Deductible on consultation",
    "Vaccination & Immunization", "Psychiatric treatment & Psychotherapy",
    "Pregnancy & Childbirth", "Dental Benefit", "Optical Benefit"
]

# -------------------- Helper Functions --------------------
def pdf_to_text(pdf_file):
    """Extract text from uploaded PDF"""
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def clean_text(text):
    """Remove extra spaces and newlines"""
    return " ".join(text.split())

def extract_with_gpt(text, fields, client, max_retries=3):
    """Extract specified fields from policy text using OpenAI GPT with retries and cleaning"""
    if client is None:
        return {f: "" for f in fields}

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

            # Auto-cleaning: extract JSON only
            idx_start = resp_text.find("{")
            idx_end = resp_text.rfind("}")
            if idx_start == -1 or idx_end == -1 or idx_end <= idx_start:
                raise ValueError("No JSON object found in GPT response.")
            resp_text = resp_text[idx_start:idx_end + 1]

            return json.loads(resp_text)

        except Exception as e:
            if attempt == max_retries - 1:
                print(f"GPT returned invalid JSON. Returning empty fields. Error: {e}")
                return {f: "" for f in fields}
            continue

def display_comparison_table(df):
    """Highlight differences in a comparison table"""
    def highlight_diff(row):
        return ['background-color: yellow' if row['Old Policy'] != row['New Policy'] else '' for _ in row]
    st.dataframe(df.style.apply(highlight_diff, axis=1))

# -------------------- Main App Logic --------------------
if mode == "Single PDF Extraction":
    pdf_type = st.selectbox("Select Payer Plan Type:", ["QLM", "ALKOOT"])
    fields_to_use = QLM_FIELDS if pdf_type == "QLM" else ALKOOT_FIELDS

    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
    if pdf_file:
        text = clean_text(pdf_to_text(pdf_file))
        data = extract_with_gpt(text, fields_to_use, client)
        st.table(pd.DataFrame(data.items(), columns=["Field", "Value"]))

else:
    col1, col2 = st.columns(2)

    with col1:
        old_pdf_type = st.selectbox("Old PDF Plan Type:", ["QLM", "ALKOOT"], key="old_type")
        old_pdf = st.file_uploader("Old Policy PDF", type=["pdf"], key="old")
    with col2:
        new_pdf_type = st.selectbox("New PDF Plan Type:", ["QLM", "ALKOOT"], key="new_type")
        new_pdf = st.file_uploader("New Policy PDF", type=["pdf"], key="new")

    if old_pdf and new_pdf:
        old_fields = QLM_FIELDS if old_pdf_type == "QLM" else ALKOOT_FIELDS
        new_fields = QLM_FIELDS if new_pdf_type == "QLM" else ALKOOT_FIELDS

        old_text = clean_text(pdf_to_text(old_pdf))
        new_text = clean_text(pdf_to_text(new_pdf))

        old_data = extract_with_gpt(old_text, old_fields, client)
        new_data = extract_with_gpt(new_text, new_fields, client)

        # Use union of fields for comparison table
        all_fields = list(set(old_fields + new_fields))
        df = pd.DataFrame({
            "Field": all_fields,
            "Old Policy": [old_data.get(f, "") for f in all_fields],
            "New Policy": [new_data.get(f, "") for f in all_fields],
        })
        display_comparison_table(df)
