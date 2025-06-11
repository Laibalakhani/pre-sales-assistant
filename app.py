import streamlit as st
import fitz  # PyMuPDF
import docx
import pandas as pd
import io
import re
from transformers import pipeline

# Page config
st.set_page_config(page_title="Pre-Sales Assistant", layout="centered")

# Load transformers models once
@st.cache_resource(show_spinner=False)
def load_models():
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    qa_model = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")
    return summarizer, qa_model

summarizer, qa_model = load_models()

# Extract text from PDF, DOCX, XLS(X)
def extract_text(file):
    if file.type == "application/pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "".join(page.get_text() for page in doc)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(io.BytesIO(file.read()))
        return "\n".join(para.text for para in doc.paragraphs)
    elif file.type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        xls = pd.ExcelFile(file)
        return "\n\n".join(df.to_string(index=False) for df in [xls.parse(s) for s in xls.sheet_names])
    return ""

# Split long text into chunks for summarization
def split_into_chunks(text, max_len=1200):
    chunks, start = [], 0
    while start < len(text):
        end = min(start + max_len, len(text))
        snippet = text[start:end]
        last_period = snippet.rfind('.')
        if last_period != -1:
            end = start + last_period + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks

# Generate improved summary
def generate_summary(text, fast_mode=False):
    chunks = split_into_chunks(text, max_len=1200)
    if fast_mode:
        chunks = chunks[:3]
    if not chunks:
        return "❌ The document is empty or could not be processed."

    summaries = []
    for i, chunk in enumerate(chunks):
        with st.spinner(f"Summarizing part {i + 1} of {len(chunks)}..."):
            try:
                result = summarizer(chunk, max_length=200, min_length=100, do_sample=False)
                summaries.append(result[0]['summary_text'])
            except Exception:
                continue

    full_summary_input = " ".join(summaries)
    try:
        final = summarizer(full_summary_input, max_length=400, min_length=200, do_sample=False)
        return final[0]['summary_text']
    except Exception:
        return full_summary_input

# QA using transformer model
def find_answer(question, text_chunks):
    context = " ".join(text_chunks[:10])  # Use first few chunks to reduce overhead
    try:
        result = qa_model(question=question, context=context)
        return result['answer']
    except:
        return "❌ Sorry, I couldn't find the answer in the document."

# Start UI
st.title("🤖 Pre-Sales Assistant")

uploaded_file = st.file_uploader("📄 Upload a document (PDF, DOCX, XLSX)", type=['pdf', 'docx', 'xls', 'xlsx'])

if uploaded_file:
    full_text = extract_text(uploaded_file)
    if len(full_text.strip()) < 50:
        st.warning("⚠️ The document appears too short or empty to summarize.")
    else:
        fast_mode = st.checkbox("⚡ Enable Fast Summary Mode (Quick but Less Detailed)", value=True)

        if st.button("Generate Summary"):
            with st.spinner("⏳ Generating summary..."):
                summary = generate_summary(full_text, fast_mode)
                st.session_state.summary = summary
                st.session_state.text_chunks = split_into_chunks(full_text)

        if "summary" in st.session_state:
            st.subheader("📝 Document Summary")
            st.write(st.session_state.summary)

            st.download_button(
                label="📥 Download Summary",
                data=st.session_state.summary,
                file_name="document_summary.txt",
                mime="text/plain"
            )

            st.subheader("💬 Ask Questions About the Document")
            question = st.text_input("Type your question:")
            if st.button("Get Answer") and question.strip():
                with st.spinner("🔍 Searching for the answer..."):
                    answer = find_answer(question, st.session_state.text_chunks)
                    st.subheader("🧠 Answer")
                    st.write(answer)
else:
    st.info("📁 Please upload a document to begin.")
