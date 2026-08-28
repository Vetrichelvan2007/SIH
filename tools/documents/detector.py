import os
from pathlib import Path
from typing import Dict, Any, Tuple

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
STRUCTURED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS | STRUCTURED_EXTENSIONS

def detect_file_type(file_path: str, filename: str = None) -> Dict[str, Any]:
    """
    Detects file type, extension, and content category.
    Returns dictionary with:
    - filename
    - extension
    - file_type
    - content_type ('image' | 'document' | 'structured' | 'unknown')
    - is_supported
    """
    name = filename or os.path.basename(file_path)
    ext = Path(name).suffix.lower()

    if ext in IMAGE_EXTENSIONS:
        content_type = "visual"
        file_type = "image"
    elif ext in STRUCTURED_EXTENSIONS:
        content_type = "structured"
        file_type = ext.lstrip(".")
    elif ext in DOCUMENT_EXTENSIONS:
        content_type = "document"
        file_type = ext.lstrip(".")
    else:
        content_type = "unknown"
        file_type = ext.lstrip(".") if ext else "unknown"

    return {
        "filename": name,
        "extension": ext,
        "file_type": file_type,
        "content_type": content_type,
        "is_supported": ext in SUPPORTED_EXTENSIONS
    }
