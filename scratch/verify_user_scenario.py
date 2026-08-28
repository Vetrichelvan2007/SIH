import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.orchestrator import AgentOrchestrator
from agent.context_manager import resolve_attachment_context, build_unified_context
from agent.intent_classifier import classify_user_intent
from agent.metadata_handler import handle_metadata_query

def verify_pandas_pdf_scenario():
    chat_id = f"pandas_session_{uuid.uuid4().hex[:8]}"
    filename = "241801313 pandas.pdf"

    print("="*75)
    print(f"VERIFYING PANDAS PDF ROUTING INTENT FOR SESSION: {chat_id}")
    print("="*75)

    pdf_data = {
        "file_type": "pdf",
        "content_type": "document",
        "filename": filename,
        "text": "# Pandas & NumPy Core Laboratory Report\nStudent Name: Alex Mercer\nRoll Number: 241801313\nTopic: Data Analysis using pandas.read_csv() and numpy.array()",
        "metadata": {"pages": 4}
    }

    # Upload PDF
    att_res = resolve_attachment_context(chat_id=chat_id, user_query="describe document", current_file_data=pdf_data)

    test_queries = [
        ("What is the student name mentioned in this document?", ["INFORMATION_EXTRACTION", "DOCUMENT_QA"], "Phi-4 Mini"),
        ("What is the student roll number?", ["INFORMATION_EXTRACTION", "DOCUMENT_QA"], "Phi-4 Mini"),
        ("What topic is described in the PDF?", ["DOCUMENT_QA"], "Phi-4 Mini"),
        ("What are the NumPy functions mentioned in the file?", ["DOCUMENT_QA"], "Phi-4 Mini"),
        ("What is the file name?", ["DOCUMENT_METADATA"], "Metadata Tool (No LLM)"),
        ("Fix the Python code in this document.", ["CODE_DEBUGGING"], "Qwen2.5-Coder"),
        ("Write a Python program based on this document.", ["CODE_GENERATION"], "Qwen2.5-Coder")
    ]

    all_passed = True
    for query, expected_tasks, expected_model in test_queries:
        orch = AgentOrchestrator(chat_id=chat_id)
        att = resolve_attachment_context(chat_id=chat_id, user_query=query, current_file_data=None, orchestrator=orch)
        intent = classify_user_intent(query, attachment_info=att)

        actual_task = intent["task_type"]
        actual_model = intent["selected_model"]

        task_ok = actual_task in expected_tasks
        model_ok = actual_model == expected_model

        status = "✓ PASS" if (task_ok and model_ok) else "✕ FAIL"
        if not (task_ok and model_ok):
            all_passed = False

        print(f"\nUser Query: '{query}'")
        print(f"  Result: {status}")
        print(f"  Task Classified: {actual_task} (Expected: {expected_tasks})")
        print(f"  Model Selected:  {actual_model} (Expected: {expected_model})")

    print("\n" + "="*75)
    if all_passed:
        print("ALL ROUTING & MODEL SELECTION CHECKS PASSED PERFECTLY!")
    else:
        print("SOME CHECKS FAILED - INSPECT LOGS ABOVE")
    print("="*75)

if __name__ == "__main__":
    verify_pandas_pdf_scenario()
