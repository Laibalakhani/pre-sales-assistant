import streamlit as st
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="Pre-Sales Assistant", layout="centered")
st.title("🤖 Local Pre-Sales Assistant")

# Upload PDF
uploaded_file = st.file_uploader("📄 Upload PDF Document", type=["pdf"])

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def summarize(text, max_sentences=5):
    sentences = re.split(r'(?<=[.!?]) +', text)
    return ' '.join(sentences[:max_sentences])

def split_into_chunks(text, max_len=500):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_len
        snippet = text[start:end]
        last_period = snippet.rfind('.')
        if last_period != -1:
            end = start + last_period + 1
        chunks.append(text[start:end].strip())
        start = end
    return chunks

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
    return best_chunk or "❌ Sorry, I couldn't find the answer."

# Process PDF
if uploaded_file:
    with st.spinner("Reading and processing PDF..."):
        pdf_text = extract_text_from_pdf(uploaded_file)
        summary = summarize(pdf_text)

    st.markdown("### 📌 PDF Summary")
    st.info(summary)

    st.markdown("### 💬 Ask a Question")
    question = st.text_input("What do you want to know?")

    if st.button("Ask"):
        chunks = split_into_chunks(pdf_text)
        answer = find_answer(question, chunks)
        st.markdown("#### ✅ Answer:")
        st.success(answer)
