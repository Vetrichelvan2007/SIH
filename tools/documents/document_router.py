import os
from typing import Dict, Any
from .detector import detect_file_type
from .pdf_processor import process_pdf
from .docx_processor import process_docx
from .pptx_processor import process_pptx
from .xlsx_processor import process_xlsx_or_csv
from .text_normalizer import normalize_text, truncate_text_if_needed

def route_and_process_document(file_path: str, filename: str = None) -> Dict[str, Any]:
    """
    Deterministic Document Router:
    Routes file to the specialized processor based on file extension and type.
    Does NOT invoke LLM reasoning.
    Returns standardized raw extraction dict:
    {
        "file_type": str,
        "content_type": str,
        "text": str,
        "visual_items": List[Dict],
        "metadata": Dict
    }
    """
    info = detect_file_type(file_path, filename=filename)
    file_type = info["file_type"]
    content_type = info["content_type"]
    name = info["filename"]

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at path: {file_path}")

    visual_items = []

    if file_type == "pdf":
        res = process_pdf(file_path)
        raw_text = res["text"]
        visual_items = res.get("visual_pages", [])
        metadata = res.get("metadata", {})

    elif file_type == "docx":
        res = process_docx(file_path)
        raw_text = res["text"]
        visual_items = res.get("embedded_images", [])
        metadata = res.get("metadata", {})

    elif file_type == "pptx":
        res = process_pptx(file_path)
        raw_text = res["text"]
        visual_items = res.get("slide_images", [])
        metadata = res.get("metadata", {})

    elif file_type in ["xlsx", "xls", "csv"]:
        res = process_xlsx_or_csv(file_path)
        raw_text = res["text"]
        metadata = res.get("metadata", {})

    elif file_type in ["txt", "md"]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        raw_text = normalize_text(content)
        metadata = {"char_count": len(raw_text), "line_count": raw_text.count("\n") + 1}

    else:
        raise ValueError(f"Unsupported document file extension: .{file_type}")

    clean_text = truncate_text_if_needed(raw_text)

    return {
        "file_type": file_type,
        "content_type": content_type,
        "filename": name,
        "text": clean_text,
        "visual_items": visual_items,
        "metadata": metadata
    }
