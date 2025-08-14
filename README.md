# Payer Plan GPT Extractor

Extract and compare QLM/ALKOOT insurance policy PDFs with GPT.

## Features
- Custom field extraction using GPT
- Compare old vs. new policies in one click
- Deployable to Streamlit Cloud with secure API key storage

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud
1. Upload this repo to GitHub.
2. Go to https://share.streamlit.io/ and deploy.
3. In App Settings → **Secrets**, add:
```
OPENAI_API_KEY="your_api_key"
```
