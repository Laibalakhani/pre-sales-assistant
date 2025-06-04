import streamlit as st
import fitz  # PyMuPDF
import docx
import pandas as pd
import io
import re
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

st.set_page_config(page_title="Pre-Sales Assistant", layout="centered")

def extract_text(file):
    file.seek(0)  # Important to reset pointer for repeated reads
    if file.type == "application/pdf":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()

    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        file.seek(0)
        doc = docx.Document(io.BytesIO(file.read()))
        fullText = [para.text for para in doc.paragraphs if para.text.strip() != '']
        return '\n'.join(fullText).strip()

    elif file.type in ["application/vnd.ms-excel",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        file.seek(0)
        xls = pd.ExcelFile(file)
        texts = []
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            texts.append(df.to_string(index=False))
        return '\n\n'.join(texts).strip()
    else:
        return ""

def summarize_text(text, sentences_count=25):
    # If text too small, just return text
    if len(text.split()) < 50:
        return text

    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = TextRankSummarizer()
    summary = summarizer(parser.document, sentences_count)
    return ' '.join(str(sentence) for sentence in summary).strip()

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

    return best_chunk or "Sorry, I couldn't find the answer in the document."

st.title("🤖 Pre-Sales Assistant")

uploaded_file = st.file_uploader(
    "Upload your document (PDF, Word, Excel)", 
    type=['pdf', 'docx', 'xls', 'xlsx']
)

if uploaded_file:
    full_text = extract_text(uploaded_file)
    if not full_text:
        st.warning("Sorry, this file type is not supported or contains no readable text.")
    else:
        st.subheader("Extracted Text Summary")
        summary_text = summarize_text(full_text, sentences_count=25)
        st.write(summary_text)

        st.download_button("Download Summary", summary_text, file_name="summary.txt")
        st.download_button("Download Full Text", full_text, file_name="full_text.txt")

        question = st.text_input("Ask a question:")

        if st.button("Get Answer") and question.strip() != "":
            chunks = split_into_chunks(full_text)
            answer = find_answer(question, chunks)
            st.markdown("### Answer:")
            st.write(answer)
