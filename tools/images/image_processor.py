import os
import io
import base64
from typing import Dict, Any
from PIL import Image

MAX_IMAGE_DIMENSION = 1280  # Resize images larger than 1280px to save VRAM/memory

def process_image(file_path_or_bytes: Any, filename: str = "image.jpg") -> Dict[str, Any]:
    """
    Validates, resizes, and base64 encodes image files (.jpg, .jpeg, .png, .webp).
    Returns:
    {
        "filename": str,
        "format": str,
        "width": int,
        "height": int,
        "base64_image": str
    }
    """
    if isinstance(file_path_or_bytes, (str, os.PathLike)):
        img = Image.open(file_path_or_bytes)
        name = filename or os.path.basename(file_path_or_bytes)
    elif isinstance(file_path_or_bytes, bytes):
        img = Image.open(io.BytesIO(file_path_or_bytes))
        name = filename
    else:
        raise ValueError("Invalid image input: expected file path string or bytes.")

    # Convert RGBA / P modes to RGB if saving to JPEG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    width, height = img.size
    
    # Resize large images to conserve GPU VRAM
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
        width, height = img.size

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "filename": name,
        "format": "jpeg",
        "width": width,
        "height": height,
        "base64_image": b64_str
    }
