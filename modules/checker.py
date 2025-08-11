import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Minimal ADGM checklist (add more from Data Sources)
ADGM_CHECKLIST = {
    "Company Incorporation": [
        "Articles of Association",
        "Memorandum of Association",
        "Board Resolution",
        "UBO Declaration Form",
        "Register of Members and Directors"
    ]
}

def check_against_checklist(detected_docs, process="Company Incorporation"):
    """Compare uploaded docs with ADGM checklist and return missing items."""
    required_docs = ADGM_CHECKLIST.get(process, [])
    missing_docs = [doc for doc in required_docs if doc not in detected_docs]
    return {
        "process": process,
        "documents_uploaded": len(detected_docs),
        "required_documents": len(required_docs),
        "missing_documents": missing_docs
    }

def run_compliance_check(doc_text, process="Company Incorporation", retrieved_context=None, model="models/gemini-2.5-pro"):
    """
    Run compliance check using Gemini + RAG context.
    retrieved_context: optional string with ADGM reference text from rag.py
    model: Gemini model to use
    """
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

    gen_model = genai.GenerativeModel(model)
    response = gen_model.generate_content(
        prompt=prompt,
        temperature=0,
        max_tokens=800,
    )

    try:
        issues = json.loads(response.text)
    except json.JSONDecodeError:
        issues = {"issues_raw": response.text.strip()}

    return issues

if __name__ == "__main__":
    # Example standalone test
    sample_docs = ["Articles of Association", "Memorandum of Association", "Board Resolution"]
    checklist_result = check_against_checklist(sample_docs)
    print("Checklist Check:", checklist_result)

    # Fake doc text for test
    fake_text = "This agreement is governed by UAE Federal Courts."
    compliance_result = run_compliance_check(fake_text)
    print("Compliance Check:", compliance_result)
