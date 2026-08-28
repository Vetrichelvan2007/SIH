import pymupdf as fitz  # PyMuPDF
import io

import base64
from typing import Dict, Any, List
from PIL import Image
from .text_normalizer import normalize_text

MIN_TEXT_WORD_COUNT = 15  # Pages below this threshold are marked as visual/scanned pages

def process_pdf(file_path: str, max_pages: int = 50) -> Dict[str, Any]:
    """
    Processes PDF files using PyMuPDF (fitz):
    1. Extracts text page by page.
    2. Identifies scanned/visual pages (low text count).
    3. Renders images ONLY for scanned/visual pages in small memory-safe batches.
    Returns:
    {
      "text": str,
      "visual_pages": [{"page": int, "type": "scanned_page", "base64_image": str}],
      "metadata": {"total_pages": int, "scanned_pages_count": int, "text_pages_count": int}
    }
    """
    doc = fitz.open(file_path)
    total_pages = len(doc)
    
    extracted_text_pages = []
    visual_pages = []
    
    pages_to_process = min(total_pages, max_pages)
    scanned_pages_count = 0
    text_pages_count = 0

    for page_idx in range(pages_to_process):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_text = page.get_text("text").strip()
        words = page_text.split()
        
        # Detect if page is visual/scanned (very few or no text words)
        is_scanned = len(words) < MIN_TEXT_WORD_COUNT
        
        if is_scanned:
            scanned_pages_count += 1
            # Render page to image (RGB) for Qwen2.5-VL processing
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("jpeg")
            b64_img = base64.b64encode(img_bytes).decode("utf-8")
            
            visual_pages.append({
                "page": page_num,
                "type": "scanned_page",
                "base64_image": b64_img
            })
            extracted_text_pages.append(f"--- Page {page_num} [Scanned/Visual Content] ---")
        else:
            text_pages_count += 1
            extracted_text_pages.append(f"--- Page {page_num} ---\n{normalize_text(page_text)}")

    doc.close()
    
    full_text = "\n\n".join(extracted_text_pages)
    
    return {
        "text": full_text,
        "visual_pages": visual_pages,
        "metadata": {
            "total_pages": total_pages,
            "processed_pages": pages_to_process,
            "scanned_pages_count": scanned_pages_count,
            "text_pages_count": text_pages_count
        }
    }
