import re
from typing import Dict, Any, List, Tuple

VISUAL_KEYWORDS = [
    "chart", "diagram", "graph", "plot", "screenshot", "layout", "visual", "figure",
    "image", "picture", "photo", "drawing", "architecture", "infographic", "wireframe",
    "table image", "scanned", "handwritten"
]

def should_trigger_vision(
    file_type: str,
    user_prompt: str = "",
    has_scanned_pages: bool = False,
    embedded_visual_count: int = 0
) -> Tuple[bool, str]:
    """
    Vision Router logic:
    Determines whether Qwen2.5-VL-3B visual processing should be triggered.
    Returns (should_use_vision: bool, reason: str).
    """
    # 1. Direct standalone image uploads ALWAYS trigger vision processing
    if file_type in ["image", "jpg", "jpeg", "png", "webp"]:
        return True, "Direct image upload requires Qwen2.5-VL-3B analysis."

    # 2. Scanned/Visual PDF pages ALWAYS trigger vision processing
    if has_scanned_pages:
        return True, "Scanned or visual PDF page detected, requiring Qwen2.5-VL-3B extraction."

    # 3. User explicitly asking visual questions about charts/diagrams/embedded images
    prompt_lower = (user_prompt or "").lower()
    has_visual_keyword = any(re.search(r'\b' + re.escape(kw) + r'\b', prompt_lower) for kw in VISUAL_KEYWORDS)

    if embedded_visual_count > 0 and has_visual_keyword:
        return True, f"User query explicitly requested visual analysis for embedded images/charts."

    # 4. Standard digital documents with clean text do NOT require vision model
    return False, "Digital document text extracted deterministically; vision model omitted to save VRAM."
