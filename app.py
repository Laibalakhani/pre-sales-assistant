import streamlit as st
import fitz  # PyMuPDF
import docx
import pandas as pd
import io
import re
from transformers import pipeline

# Set the Streamlit page config
st.set_page_config(page_title="Pre-Sales Assistant")

@st.cache_resource(show_spinner=False)
def load_summarizer():
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

summarizer = load_summarizer()

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
        return ""

def split_into_chunks(text, max_len=1200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_len
        snippet = text[start:end]
        last_period = snippet.rfind('.')
        if last_period != -1:
            end = start + last_period + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks

def generate_summary(text):
    chunks = split_into_chunks(text)
    if not chunks:
        return "The document is empty or could not be processed."

    summaries = []
    for chunk in chunks:
        try:
            result = summarizer(chunk, max_length=150, min_length=80, do_sample=False)
            summaries.append(result[0]['summary_text'])
        except Exception:
            summaries.append("")

    combined_summary_text = " ".join(summaries).strip()
    if not combined_summary_text:
        return "Could not generate summary from document content."

    try:
        final_summary = summarizer(combined_summary_text, max_length=180, min_length=100, do_sample=False)
        return final_summary[0]['summary_text']
    except Exception:
        return combined_summary_text

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

st.title("🤖 Pre-Sales Assistant")

uploaded_file = st.file_uploader("📄 Upload your document", type=['pdf', 'docx', 'xls', 'xlsx'])

if uploaded_file:
    full_text = extract_text(uploaded_file)

    if len(full_text.strip()) < 50:
        st.warning("The document appears to be too short or empty to summarize.")
    else:
        with st.spinner("Summarizing the document, please wait..."):
            summary = generate_summary(full_text)

        st.markdown("### 📝 Document Summary")
        st.write(summary)

        # Add download button for summary as txt file
        st.download_button(
            label="📥 Download Summary",
            data=summary,
            file_name="document_summary.txt",
            mime="text/plain"
        )

        text_chunks = split_into_chunks(full_text, max_len=1200)

        question = st.text_input("Ask a question about the document:")
        if st.button("Get Answer") and question.strip() != "":
            answer = find_answer(question, text_chunks)
            st.markdown("### 🧠 Answer:")
            st.write(answer)
else:
    st.info("Please upload a document to get started.")
