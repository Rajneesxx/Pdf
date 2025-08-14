import streamlit as st
import pdfplumber
import pandas as pd
from openai import OpenAI

st.set_page_config(page_title="Payer Plan GPT Extractor", layout="wide")
st.title("🤖 Payer Plan Field Extractor with GPT (Updated)")

mode = st.radio("Choose Mode:", ["Single PDF Extraction", "Compare Two PDFs"])

# Initialize OpenAI client
client = None
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    key_input = st.text_input("Enter OpenAI API Key:", type="password")
    if key_input:
        client = OpenAI(api_key=key_input)

def pdf_to_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def extract_with_gpt(text, fields):
    if client is None:
        return {f: "" for f in fields}
    prompt = f"Extract these fields from the policy text:\n{', '.join(fields)}\n\nText:\n{text}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    import json
    try:
        return json.loads(resp.choices[0].message.content)
    except:
        return {f: "" for f in fields}

fields_input = st.text_area("Fields to extract (one per line):", "Policy No\nPeriod of Insurance\nPlan")
target_fields = [f.strip() for f in fields_input.split("\n") if f.strip()]

if mode == "Single PDF Extraction":
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
    if pdf_file and client is not None:
        text = pdf_to_text(pdf_file)
        data = extract_with_gpt(text, target_fields)
        st.table(pd.DataFrame(data.items(), columns=["Field", "Value"]))

else:
    col1, col2 = st.columns(2)
    with col1:
        old_pdf = st.file_uploader("Old Policy PDF", type=["pdf"], key="old")
    with col2:
        new_pdf = st.file_uploader("New Policy PDF", type=["pdf"], key="new")
    if old_pdf and new_pdf and client is not None:
        old_data = extract_with_gpt(pdf_to_text(old_pdf), target_fields)
        new_data = extract_with_gpt(pdf_to_text(new_pdf), target_fields)
        df = pd.DataFrame({
            "Field": target_fields,
            "Old Policy": [old_data.get(f, "") for f in target_fields],
            "New Policy": [new_data.get(f, "") for f in target_fields],
        })
        st.table(df)
