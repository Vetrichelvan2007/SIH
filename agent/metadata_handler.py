import re
from typing import Dict, Any, Optional

def handle_metadata_query(
    user_query: str,
    attachment_info: Optional[Dict[str, Any]] = None,
    orchestrator: Optional[Any] = None
) -> str:
    """
    Direct Metadata Tool Handler:
    Answers metadata questions (e.g. filename, page count, format) directly from attachment properties
    without calling an LLM.
    """
    if orchestrator:
        s_meta = orchestrator.start_step(
            type="tool",
            component="metadata_tool",
            action="document_metadata_retrieval",
            input_summary=f"Metadata Query: '{user_query}'",
            passed_to="User Interface"
        )

    if not attachment_info or not attachment_info.get("resolved"):
        msg = "No document is currently attached to this conversation. Please upload or attach a file to inspect its metadata."
        if orchestrator:
            orchestrator.complete_step(s_meta, output_summary=msg)
        return msg

    filename = attachment_info.get("filename", "Unknown File")
    file_type = (attachment_info.get("file_type") or "file").upper()
    page_count = attachment_info.get("page_count") or attachment_info.get("metadata", {}).get("pages") or 1
    content_type = attachment_info.get("content_type", "document")
    meta = attachment_info.get("metadata", {})

    q_lower = user_query.lower()

    if "name" in q_lower or "filename" in q_lower:
        response = f"The attached document file name is `{filename}`."
    elif "page" in q_lower:
        response = f"The document `{filename}` contains {page_count} page(s)."
    elif "format" in q_lower or "type" in q_lower:
        response = f"The document `{filename}` is in `{file_type}` format ({content_type} category)."
    else:
        response = f"Attachment Details:\n- File Name: `{filename}`\n- Format: `{file_type}`\n- Page Count: {page_count}\n- Category: {content_type.capitalize()}"

    if orchestrator:
        orchestrator.complete_step(s_meta, output_summary=f"Retrieved metadata for '{filename}'")
        orchestrator.set_final_generator("Metadata Tool (No LLM)", "metadata_tool", is_vision=False)

    return response
