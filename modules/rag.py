import os
import json
import pickle
import subprocess
import sys
import faiss
import numpy as np
from PyPDF2 import PdfReader
from docx import Document
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

INDEX_DIR = "data/embeddings"
INDEX_PATH = os.path.join(INDEX_DIR, "adgm_faiss.index")
MAPPING_PATH = os.path.join(INDEX_DIR, "doc_mapping.pkl")
REFERENCE_DIR = "data/reference_docs"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")

def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == ".pdf":
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif ext == ".docx":
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for entry in data:
                    if "Passage" in entry:
                        text += entry["Passage"] + "\n"
                    elif "Question" in entry:
                        text += entry["Question"] + "\n"
            elif isinstance(data, dict):
                text = json.dumps(data)

    return text.strip()

def get_embedding(text):
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text
    )
    return result["embedding"]

def create_embeddings_for_reference_docs():
    os.makedirs(INDEX_DIR, exist_ok=True)
    doc_texts = []
    doc_mapping = {}

    for root, _, files in os.walk(REFERENCE_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            text = extract_text_from_file(file_path)
            if text:
                chunks = chunk_text(text)
                for chunk in chunks:
                    doc_texts.append(chunk)
                    doc_mapping[len(doc_texts) - 1] = {
                        "file": file,
                        "text": chunk
                    }

    if not doc_texts:
        raise ValueError("No valid reference documents found in data/reference_docs/")

    embeddings = [get_embedding(t) for t in doc_texts]

    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype("float32"))

    faiss.write_index(index, INDEX_PATH)
    with open(MAPPING_PATH, "wb") as f:
        pickle.dump(doc_mapping, f)

def retrieve_context(query, top_k=5):
    if not os.path.exists(INDEX_PATH) or not os.path.exists(MAPPING_PATH):
        raise FileNotFoundError("FAISS index not found. Run create_embeddings_for_reference_docs() first.")

    index = faiss.read_index(INDEX_PATH)

    with open(MAPPING_PATH, "rb") as f:
        doc_mapping = pickle.load(f)

    query_vector = np.array([get_embedding(query)], dtype="float32")

    distances, indices = index.search(query_vector, top_k)

    results = []
    for idx in indices[0]:
        if idx in doc_mapping:
            results.append(doc_mapping[idx])

    return results
