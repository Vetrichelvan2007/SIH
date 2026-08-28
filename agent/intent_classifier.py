import re
from enum import Enum
from typing import Dict, Any, Optional

class TaskType(str, Enum):
    GENERAL_QA = "GENERAL_QA"
    DOCUMENT_QA = "DOCUMENT_QA"
    DOCUMENT_SUMMARIZATION = "DOCUMENT_SUMMARIZATION"
    INFORMATION_EXTRACTION = "INFORMATION_EXTRACTION"
    DOCUMENT_METADATA = "DOCUMENT_METADATA"
    VISION_QA = "VISION_QA"
    CODE_EXPLANATION = "CODE_EXPLANATION"
    CODE_GENERATION = "CODE_GENERATION"
    CODE_DEBUGGING = "CODE_DEBUGGING"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    MATH = "MATH"
    OTHER = "OTHER"

def classify_user_intent(user_query: str, attachment_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    User Intent Classifier:
    Separates Document Subject from User Intent.
    Evaluates what the USER is asking the system to do independently of programming terms in document context.
    """
    if not user_query:
        return {
            "task_type": TaskType.GENERAL_QA.value,
            "user_intent": "general_question",
            "domain": "GENERAL",
            "selected_model": "Phi-4 Mini",
            "model_id": "phi4-mini"
        }

    q_lower = user_query.lower().strip()
    has_attachment = bool(attachment_info and attachment_info.get("resolved"))
    att_type = attachment_info.get("content_type", "") if attachment_info else ""
    is_visual = att_type in ["visual", "image"] or (attachment_info and attachment_info.get("file_type") in ["png", "jpg", "jpeg", "webp"])

    # 1. DOCUMENT METADATA CHECK (Highest Priority for Metadata Questions)
    metadata_patterns = [
        r"\bfile\s*name\b", r"\bfilename\b", r"\bname of the file\b", r"\bname of the pdf\b",
        r"\bname of the document\b", r"\bhow many pages\b", r"\bpage count\b", r"\bfile format\b", r"\bfile type\b"
    ]
    if any(re.search(pat, q_lower) for pat in metadata_patterns):
        return {
            "task_type": TaskType.DOCUMENT_METADATA.value,
            "user_intent": "document_metadata_query",
            "domain": "DOCUMENT",
            "selected_model": "Metadata Tool (No LLM)",
            "model_id": "metadata_tool",
            "is_metadata_query": True
        }

    # 2. EXPLICIT CODING INTENT CHECK
    # User MUST ask to write, generate, fix, debug, or explain code for Coding tasks
    code_gen_patterns = [
        r"\bwrite\s+(a\s+)?(python|js|javascript|code|script|program|function)\b",
        r"\bcreate\s+(a\s+)?(python|js|code|script|program|function)\b",
        r"\bgenerate\s+(a\s+)?(python|js|code|script|program)\b",
        r"\bauthor\s+(a\s+)?(script|code)\b",
        r"\bwrite a python program\b"
    ]
    code_debug_patterns = [
        r"\bfix\s+(the\s+)?(python|js|code|bug|error|script)\b",
        r"\bdebug\s+(the\s+)?(python|js|code|program|script|function)\b",
        r"\bsolve\s+(the\s+)?(syntax error|bug|issue in code)\b",
        r"\brefactor\s+code\b"
    ]
    code_explain_patterns = [
        r"\bexplain\s+(the\s+)?(python|js|code|script|function|algorithm)\b",
        r"\bhow does this code work\b"
    ]

    if any(re.search(pat, q_lower) for pat in code_gen_patterns):
        return {
            "task_type": TaskType.CODE_GENERATION.value,
            "user_intent": "code_generation",
            "domain": "CODING",
            "selected_model": "Qwen2.5-Coder",
            "model_id": "qwen2.5-coder"
        }
    if any(re.search(pat, q_lower) for pat in code_debug_patterns):
        return {
            "task_type": TaskType.CODE_DEBUGGING.value,
            "user_intent": "code_debugging",
            "domain": "CODING",
            "selected_model": "Qwen2.5-Coder",
            "model_id": "qwen2.5-coder"
        }
    if any(re.search(pat, q_lower) for pat in code_explain_patterns):
        return {
            "task_type": TaskType.CODE_EXPLANATION.value,
            "user_intent": "code_explanation",
            "domain": "CODING",
            "selected_model": "Qwen2.5-Coder",
            "model_id": "qwen2.5-coder"
        }

    # 3. VISION QA CHECK
    if is_visual or re.search(r"\bdescribe this image\b|\bwhat is shown on\b|\blook at image\b|\bchart detail\b", q_lower):
        return {
            "task_type": TaskType.VISION_QA.value,
            "user_intent": "visual_question_answering",
            "domain": "VISION",
            "selected_model": "Qwen2.5-VL-3B",
            "model_id": "qwen2.5vl:3b"
        }

    # 4. INFORMATION EXTRACTION CHECK
    info_extract_patterns = [
        r"\bstudent\s*name\b", r"\bstudent\s*roll\b", r"\broll\s*number\b", r"\bwho'?s\s*name\b",
        r"\bauthor\s*name\b", r"\bextract\b", r"\bfind\s+(the\s+)?(name|date|roll|id|number|email)\b"
    ]
    if any(re.search(pat, q_lower) for pat in info_extract_patterns):
        return {
            "task_type": TaskType.INFORMATION_EXTRACTION.value,
            "user_intent": "information_extraction",
            "domain": "DOCUMENT",
            "selected_model": "Phi-4 Mini",
            "model_id": "phi4-mini"
        }

    # 5. DOCUMENT SUMMARIZATION CHECK
    summarize_patterns = [
        r"\bsummarize\b", r"\bsummary\b", r"\bgive\s+(the\s+)?important\s+points\b",
        r"\bmain\s+takeaways\b", r"\boverview of\b"
    ]
    if any(re.search(pat, q_lower) for pat in summarize_patterns):
        return {
            "task_type": TaskType.DOCUMENT_SUMMARIZATION.value,
            "user_intent": "document_summarization",
            "domain": "DOCUMENT",
            "selected_model": "Phi-4 Mini",
            "model_id": "phi4-mini"
        }

    # 6. DOCUMENT QA CHECK (Questions referencing file, pdf, document, functions in file, topic in pdf)
    doc_qa_patterns = [
        r"\bpdf\b", r"\bfile\b", r"\bdocument\b", r"\bdoc\b", r"\bin this file\b", r"\bin the pdf\b",
        r"\bmentioned in\b", r"\bdescribed in\b", r"\btopic\b", r"\bwhat does df mean\b", r"\bexplain page\b"
    ]
    if has_attachment or any(re.search(pat, q_lower) for pat in doc_qa_patterns):
        return {
            "task_type": TaskType.DOCUMENT_QA.value,
            "user_intent": "document_question_answering",
            "domain": "DOCUMENT",
            "selected_model": "Phi-4 Mini",
            "model_id": "phi4-mini"
        }

    # 7. MATH / REASONING CHECK
    if re.search(r"\b(math|calculate|equation|algebra|solve|proof)\b", q_lower) or re.search(r"\d+\s*[\+\-\*\×x\/]\s*\d+", q_lower):
        return {
            "task_type": TaskType.MATH.value,
            "user_intent": "mathematical_reasoning",
            "domain": "REASONING",
            "selected_model": "Phi-4 Mini",
            "model_id": "phi4-mini"
        }

    # 8. DEFAULT GENERAL QA
    return {
        "task_type": TaskType.GENERAL_QA.value,
        "user_intent": "general_qa",
        "domain": "GENERAL",
        "selected_model": "Phi-4 Mini",
        "model_id": "phi4-mini"
    }
