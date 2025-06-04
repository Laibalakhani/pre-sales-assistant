import streamlit as st
import fitz  # PyMuPDF
import docx
import pandas as pd
import io
import re
from transformers import pipeline
import torch

# Set the Streamlit page config
st.set_page_config(page_title="Pre-Sales Assistant")

# Load the Hugging Face summarizer
@st.cache_resource(show_spinner=False)
def load_summarizer():
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

summarizer = load_summarizer()

# Extract text from supported file types
def extract_text(file):
    if file.type == "application/pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(io.BytesIO(file.read()))
        return "\n".join(para.text for para in doc.paragraphs)

    elif file.type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        xls = pd.ExcelFile(file)
        texts = []
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            texts.append(df.to_string(index=False))
        return '\n\n'.join(texts)

    else:
        return "Unsupported file type."

# Split text into manageable chunks
def split_into_chunks(text, max_len=1000):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_len
        snippet = text[start:end]
        last_period = snippet.rfind('.')
        if last_period != -1:
            end = start + last_period + 1
        chunk = text[start:end].strip()
        if chunk:  # Skip empty
            chunks.append(chunk)
        start = end
    return chunks

# Summarize using Hugging Face summarizer
def summarize_text(text, max_length=400):
    chunks = split_into_chunks(text, max_len=1000)
    summaries = []

    for chunk in chunks:
        try:
            result = summarizer(chunk, max_length=max_length, min_length=30, do_sample=False)
            summaries.append(result[0]['summary_text'])
        except Exception as e:
            summaries.append(f"[Error summarizing chunk: {e}]")

    return " ".join(summaries) if summaries else "[No summary generated.]"

# Simple keyword-based answer matching
def find_answer(question, text_chunks):
    question_words = set(re.findall(r'\w+', question.lower()))
    best_chunk = None
    max_matches = 0

    for chunk in text_chunks:
        chunk_words = set(re.findall(r'\w+', chunk.lower()))
        common_words = question_words.intersection(chunk_words)
        if len(common_words) > max_matches:
            max_matches = len(common_words)
            best_chunk = chunk

    return best_chunk or "Sorry, I couldn't find the answer in the document."

# UI
st.title("🤖 Pre-Sales Assistant")
uploaded_file = st.file_uploader("📄 Upload your document", type=['pdf', 'docx', 'xls', 'xlsx'])

if uploaded_file:
    full_text = extract_text(uploaded_file)
    st.write("📄 Document Length:", len(full_text), "characters")
    st.text_area("🔍 Preview Extracted Text", full_text[:3000], height=200)

uploaded_file = st.file_uploader("📄 Upload your document", type=['pdf', 'docx', 'xls', 'xlsx'])

if uploaded_file:
    full_text = extract_text(uploaded_file)

    st.subheader("📝 Extracted Text Summary")

    if len(full_text.strip()) > 50:
        with st.spinner("Summarizing... please wait."):
            try:
                chunks = split_into_chunks(full_text, max_len=1000)
                chunks = chunks[:3]  # TEMP: summarize only first 3 chunks

                summaries = []
                for i, chunk in enumerate(chunks):
                    st.info(f"Summarizing chunk {i + 1}/{len(chunks)}...")
                    result = summarizer(chunk, max_length=400, min_length=30, do_sample=False)
                    summaries.append(result[0]['summary_text'])

                summary_text = " ".join(summaries)
                st.success("✅ Summary generated.")
                st.write(summary_text)
                st.download_button("📥 Download Summary", summary_text, file_name="summary.txt")
            except Exception as e:
                st.error(f"❌ Summarization failed: {e}")
    else:
        st.warning("Extracted text is too short or empty to summarize.")

    st.download_button("📥 Download Full Text", full_text, file_name="full_text.txt")
    question = st.text_input("Ask a question:")
    if st.button("Get Answer") and question.strip() != "":
        chunks = split_into_chunks(full_text)
        answer = find_answer(question, chunks)
        st.markdown("### 🧠 Answer:")
        st.write(answer)
else:
    st.info("Please upload a document to proceed.")
