import re

def normalize_text(text: str) -> str:
    """
    Normalizes text encodings, strips excess whitespace, and cleans up line breaks.
    """
    if not text:
        return ""
    
    # Replace non-breaking spaces and weird control characters
    text = text.replace('\xa0', ' ').replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove trailing whitespace from lines
    lines = [line.rstrip() for line in text.split('\n')]
    
    # Collapse 3+ consecutive newlines into 2
    cleaned = '\n'.join(lines)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()

def truncate_text_if_needed(text: str, max_chars: int = 40000) -> str:
    """
    Truncates text if it exceeds max_chars, leaving a note.
    """
    if len(text) <= max_chars:
        return text
    
    half = max_chars // 2
    head = text[:half]
    tail = text[-half:]
    return f"{head}\n\n... [Content Truncated ({len(text)} characters total)] ...\n\n{tail}"
