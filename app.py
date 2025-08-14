
import streamlit as st
import pdfplumber
import pandas as pd
from openai import OpenAI
import json

st.set_page_config(page_title="Payer Plan GPT Extractor", layout="wide")
st.title("🤖 Payer Plan Field Extractor with GPT (Enhanced)")

mode = st.radio("Choose Mode:", ["Single PDF Extraction", "Compare Two PDFs"])

# Initialize OpenAI client
from openai import OpenAI

api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key not found! Add it in Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)
res = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0,
)

data = res.choices[0].message.content  # this contains the extracted text


def pdf_to_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def clean_text(text):
    return ' '.join(text.split())  # remove extra spaces and newlines

def extract_with_gpt(text, fields):
    if client is None:
        return {f: "" for f in fields}
    prompt = f"""
You are a data extraction assistant.
Extract ONLY the following fields from the insurance policy text.
Fields: {fields}

Return a valid JSON object with keys exactly matching the field names.
If a field is not found, set its value to an empty string.

Policy Text:
{text}
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except:
        return {f: "" for f in fields}

fields_input = st.text_area("Fields to extract (one per line):", "Policy No\nPeriod of Insurance\nPlan")
target_fields = [f.strip() for f in fields_input.split("\n") if f.strip()]

def display_comparison_table(df):
    # Highlight differences
    def highlight_diff(row):
        return ['background-color: yellow' if row['Old Policy'] != row['New Policy'] else '' for _ in row]
    st.dataframe(df.style.apply(highlight_diff, axis=1))

if mode == "Single PDF Extraction":
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
    if pdf_file and client is not None:
        text = clean_text(pdf_to_text(pdf_file))
        data = extract_with_gpt(text, target_fields)
        st.table(pd.DataFrame(data.items(), columns=["Field", "Value"]))

else:
    col1, col2 = st.columns(2)
    with col1:
        old_pdf = st.file_uploader("Old Policy PDF", type=["pdf"], key="old")
    with col2:
        new_pdf = st.file_uploader("New Policy PDF", type=["pdf"], key="new")
    if old_pdf and new_pdf and client is not None:
        old_data = extract_with_gpt(clean_text(pdf_to_text(old_pdf)), target_fields)
        new_data = extract_with_gpt(clean_text(pdf_to_text(new_pdf)), target_fields)
        df = pd.DataFrame({
            "Field": target_fields,
            "Old Policy": [old_data.get(f, "") for f in target_fields],
            "New Policy": [new_data.get(f, "") for f in target_fields],
        })
        display_comparison_table(df)
