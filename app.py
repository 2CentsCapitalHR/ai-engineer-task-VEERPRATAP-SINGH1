import os
import json
import gradio as gr
from dotenv import load_dotenv
from modules.parser import parse_uploaded_doc
from modules.checker import check_against_checklist, run_compliance_check
from modules.rag import retrieve_context, create_embeddings_for_reference_docs
from modules.docx_tools import add_comments_to_docx
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gemini-2.5-pro")

INDEX_PATH = "data/embeddings/adgm_faiss.index"

def ensure_faiss_index():
    if not os.path.exists(INDEX_PATH):
        create_embeddings_for_reference_docs()

def run_compliance_check(doc_text, process="Company Incorporation", retrieved_context=None):
    context_str = retrieved_context if retrieved_context else "No additional context."
    prompt = f"""
    You are an ADGM compliance assistant.
    Task: Review the provided document for:
      - Missing clauses
      - Wrong jurisdiction (should be ADGM)
      - Missing signatory blocks
      - Non-compliance with ADGM templates
    Provide output in JSON format with keys: document, section, issue, severity, suggestion.

    Context from ADGM reference docs:
    {context_str}

    Document Text:
    {doc_text}
    """

    model = genai.GenerativeModel(GENERATION_MODEL)
    response = model.generate_content(prompt)

    try:
        issues = json.loads(response.text)
    except json.JSONDecodeError:
        issues = {"issues_raw": response.text.strip()}

    return issues

def process_document(file_path):
    try:
        ensure_faiss_index()
        parsed = parse_uploaded_doc(file_path)
        doc_type = parsed["document_type"]
        doc_text = parsed["document_text"]
        checklist_result = check_against_checklist([doc_type])
        retrieved_context = retrieve_context(f"{doc_type} ADGM requirements and related regulatory clauses")
        issues = run_compliance_check(
            doc_text,
            process="Company Incorporation",
            retrieved_context=retrieved_context
        )
        issues_list = issues.get("issues_found", [])
        reviewed_path = add_comments_to_docx(file_path, issues_list)
        output_json = {
            "checklist_result": checklist_result,
            "issues": issues
        }
        return output_json, reviewed_path

    except Exception as e:
        return {"error": str(e)}, None

# Gradio UI part unchanged...

# --------- Gradio Interface ---------
with gr.Blocks() as demo:
    gr.Markdown("# 🏛️ ADGM Corporate Agent (Prototype)")
    gr.Markdown("Attach a `.docx` file from your system for **ADGM compliance review**.")

    with gr.Row():
        file_input = gr.File(
            file_types=[".docx"],
            type="filepath",
            label="Upload Legal Document (.docx)"
        )

    with gr.Row():
        json_output = gr.JSON(label="Checklist + Compliance Findings")

    with gr.Row():
        reviewed_doc_output = gr.File(label="Download Reviewed Document (with comments)")

    run_btn = gr.Button("Run Compliance Review")

    run_btn.click(
        fn=process_document,
        inputs=file_input,
        outputs=[json_output, reviewed_doc_output]
    )

if __name__ == "__main__":
    demo.launch()
