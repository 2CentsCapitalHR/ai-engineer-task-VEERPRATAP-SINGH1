from docx import Document
import os

# Basic keyword-based classification for prototype
DOC_TYPE_KEYWORDS = {
    "Articles of Association": ["articles of association", "aoa"],
    "Memorandum of Association": ["memorandum of association", "moa", "mou"],
    "Board Resolution": ["board resolution", "board of directors"],
    "UBO Declaration Form": ["ubo", "ultimate beneficial owner"],
    "Register of Members and Directors": ["register of members", "register of directors"]
}

def extract_text_from_docx(file_path):
    """Extract all text from a .docx file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    doc = Document(file_path)
    text = "\n".join([para.text.strip() for para in doc.paragraphs if para.text.strip()])
    return text

def classify_document(text):
    """
    Classify document type based on keyword search.
    Returns matched type or 'Unknown Document'.
    """
    lower_text = text.lower()
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        if any(keyword in lower_text for keyword in keywords):
            return doc_type
    return "Unknown Document"

def parse_uploaded_doc(file_path):
    """
    Full parsing pipeline: extract text + classify type.
    Returns dict with type and text.
    """
    text = extract_text_from_docx(file_path)
    doc_type = classify_document(text)
    return {
        "document_type": doc_type,
        "document_text": text
    }

if __name__ == "__main__":
    # Example standalone test
    sample_file = "data/sample_docs/sample_aos.docx"  # Replace with your file
    parsed = parse_uploaded_doc(sample_file)
    print("Detected Document Type:", parsed["document_type"])
    print("Preview of Text:\n", parsed["document_text"][:300], "...")
