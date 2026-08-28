import re

def summarize_text(text: str, max_len: int = 140) -> str:
    """
    Returns a clean, safe single-line summary preview of input or output text.
    """
    if not text:
        return "No text data"
    
    # Strip markdown headers, code fences, and excess whitespace
    clean = text.replace("```json", "").replace("```", "").replace("#", "").strip()
    clean = re.sub(r'\s+', ' ', clean)

    if len(clean) <= max_len:
        return clean
    return f"{clean[:max_len]}..."

def summarize_image_input(filename: str = "", width: int = 0, height: int = 0) -> str:
    """
    Summarizes image input properties safely.
    """
    dims = f" ({width}x{height}px)" if width and height else ""
    name = filename or "Uploaded Image"
    return f"Image: '{name}'{dims}"

def summarize_document_input(filename: str, file_type: str) -> str:
    """
    Summarizes document file input properties.
    """
    return f"Document: '{filename}' ({file_type.upper()})"

def summarize_vision_output(analysis: str) -> str:
    """
    Summarizes Qwen2.5-VL-3B vision model response.
    """
    if not analysis:
        return "No visual analysis generated"
    if "[Vision Processing Error" in analysis:
        return analysis
    return f"Vision output: {summarize_text(analysis, 120)}"

def summarize_input_type(attachment_info: Optional[dict] = None) -> str:
    """
    Returns precise input type and format string (e.g. 'DOCUMENT (PDF)', 'IMAGE (PNG)', 'TEXT').
    """
    if not attachment_info or not attachment_info.get("resolved"):
        return "TEXT"
    
    file_type = (attachment_info.get("file_type") or "file").upper()
    content_type = attachment_info.get("content_type", "")
    
    if content_type == "visual" or file_type in ["PNG", "JPG", "JPEG", "WEBP"]:
        return f"IMAGE ({file_type})"
    return f"DOCUMENT ({file_type})"

