import re
from typing import Dict, Any, List, Optional, Tuple

from agent.state import (
    register_attachment,
    get_chat_attachments,
    get_latest_attachment
)
from agent.trace_events import summarize_text

DOCUMENT_TRIGGER_PATTERNS = [
    r"\bpdf\b", r"\bfile\b", r"\bdocument\b", r"\bdoc\b", r"\bimage\b", r"\bpicture\b",
    r"\bscreenshot\b", r"\bpage\b", r"\btable\b", r"\bchart\b", r"\bdiagram\b", r"\bsection\b",
    r"\bnumpy\b", r"\bauthor\b", r"\bname\b", r"\bfunction\b", r"\bfunctions\b", r"\bsummary\b",
    r"\bmentioned\b", r"\bdescribed\b", r"\bread\b", r"\bexplain page\b", r"\bextract\b"
]

def is_document_grounded_query(user_query: str) -> Tuple[bool, str]:
    """
    Detects whether user query explicitly or implicitly refers to an uploaded document, PDF, or image.
    Returns (is_grounded, matching_reason).
    """
    if not user_query:
        return False, ""
    
    q_lower = user_query.lower()
    for pattern in DOCUMENT_TRIGGER_PATTERNS:
        if re.search(pattern, q_lower):
            return True, f"Matched keyword/pattern '{pattern}'"
            
    return False, ""

def extract_requested_page(user_query: str) -> Optional[int]:
    """
    Extracts page number if user query specifies e.g. 'page 2', 'page 3'.
    """
    match = re.search(r"\bpage\s*(\d+)\b", user_query.lower())
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None

def resolve_attachment_context(
    chat_id: str,
    user_query: str,
    current_file_data: Optional[Dict[str, Any]] = None,
    orchestrator: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Attachment Context Resolver:
    1. If current_file_data is present, register attachment in state.
    2. If current_file_data is None, inspect conversation state for active attachments.
    3. If query is document-grounded but no attachment exists, activate Hallucination Prevention Guard.
    4. Log empirical trace steps: state resolution, attachment resolution, context retrieval.
    """
    # --------------------------------------------------
    # CASE 1: NEW FILE UPLOADED IN CURRENT REQUEST
    # --------------------------------------------------
    if current_file_data:
        filename = current_file_data.get("filename") or current_file_data.get("metadata", {}).get("filename") or "Attached File"
        file_type = current_file_data.get("file_type", "document")
        content_type = current_file_data.get("content_type", "document")
        
        registered = register_attachment(
            chat_id=chat_id,
            filename=filename,
            file_type=file_type,
            content_type=content_type,
            result_dict=current_file_data
        )
        
        if orchestrator:
            s1 = orchestrator.start_step(
                type="context",
                component="conversation_state",
                action="conversation_state_resolution",
                input_summary=f"Chat ID: {chat_id[:8]}",
                passed_to="attachment_resolver"
            )
            orchestrator.complete_step(s1, output_summary=f"Registered new attachment: '{filename}'")

            s2 = orchestrator.start_step(
                type="context",
                component="attachment_resolver",
                action="attachment_reference_resolution",
                input_summary=f"File: '{filename}' ({file_type.upper()})",
                passed_to="context_builder"
            )
            orchestrator.complete_step(s2, output_summary=f"Resolved attachment: '{filename}'")

        return {
            "resolved": True,
            "is_new": True,
            "attachment_id": registered["attachment_id"],
            "filename": filename,
            "file_type": file_type,
            "content_type": content_type,
            "text": current_file_data.get("text", ""),
            "visual_content": current_file_data.get("visual_content", []),
            "analysis": current_file_data.get("analysis"),
            "metadata": current_file_data.get("metadata", {})
        }

    # --------------------------------------------------
    # CASE 2: FOLLOW-UP QUERY (NO NEW FILE ATTACHMENT)
    # --------------------------------------------------
    all_attachments = get_chat_attachments(chat_id)
    is_grounded, ground_reason = is_document_grounded_query(user_query)

    if orchestrator:
        s1 = orchestrator.start_step(
            type="context",
            component="conversation_state",
            action="conversation_state_resolution",
            input_summary=f"Session: {chat_id[:8]} | Attachments found: {len(all_attachments)}",
            passed_to="attachment_resolver"
        )
        orchestrator.complete_step(
            s1,
            output_summary=f"State resolved: {len(all_attachments)} attachments registered in conversation"
        )

    # Hallucination Prevention Guard
    if not all_attachments:
        if is_grounded:
            if orchestrator:
                s_guard = orchestrator.start_step(
                    type="context",
                    component="hallucination_guard",
                    action="attachment_validation",
                    input_summary=f"Query requires document context: {ground_reason}",
                    passed_to="User Interface"
                )
                orchestrator.fail_step(
                    s_guard,
                    error_message="No document context found for document-grounded query",
                    fallback_action="Prompt user to reattach document"
                )

            return {
                "resolved": False,
                "is_grounded_query": True,
                "reason": "missing_attachment",
                "notice_response": "I don't currently have access to the document or file contents in this conversation. Please upload or attach the file (PDF, Image, DOCX, XLSX, etc.) so I can accurately answer your question."
            }

        return {"resolved": False, "is_grounded_query": False}

    # Resolve specific attachment if multiple exist
    target_att = None
    if len(all_attachments) == 1:
        target_att = all_attachments[0]
    else:
        # Match explicit filename if user mentions it
        q_lower = user_query.lower()
        for att in all_attachments:
            if att["filename"].lower() in q_lower:
                target_att = att
                break
        if not target_att:
            target_att = all_attachments[-1]  # Default to latest attachment

    filename = target_att["filename"]
    res_dict = target_att.get("result", {})
    doc_text = res_dict.get("text", "")
    vis_content = res_dict.get("visual_content", [])
    overall_analysis = res_dict.get("analysis")
    pages_count = target_att.get("page_count", 1)

    # Check for specific page filtering (e.g., "explain page 2")
    req_page = extract_requested_page(user_query)
    if req_page:
        page_marker = f"--- Page {req_page} ---"
        if page_marker in doc_text:
            # Extract text specifically for requested page
            parts = doc_text.split(page_marker)
            if len(parts) > 1:
                next_part = parts[1].split("--- Page ")[0]
                doc_text = f"--- Page {req_page} ---\n{next_part.strip()}"

    if orchestrator:
        s2 = orchestrator.start_step(
            type="context",
            component="attachment_resolver",
            action="attachment_reference_resolution",
            input_summary=f"Resolved file: '{filename}'",
            passed_to="context_builder"
        )
        orchestrator.complete_step(
            s2,
            output_summary=f"Resolved active attachment: '{filename}' (ID: {target_att['attachment_id']})"
        )

        s3 = orchestrator.start_step(
            type="context",
            component="context_retriever",
            action="document_context_retrieved",
            input_summary=f"Pages: {pages_count} | Chars: {len(doc_text)}",
            passed_to="context_builder"
        )
        orchestrator.complete_step(
            s3,
            output_summary=f"Retrieved document text ({len(doc_text)} chars) + {len(vis_content)} visual items"
        )

    return {
        "resolved": True,
        "is_new": False,
        "attachment_id": target_att["attachment_id"],
        "filename": filename,
        "file_type": target_att["file_type"],
        "content_type": target_att["content_type"],
        "text": doc_text,
        "visual_content": vis_content,
        "analysis": overall_analysis,
        "page_count": pages_count,
        "metadata": res_dict.get("metadata", {})
    }

def build_unified_context(
    user_query: str,
    attachment_res: Dict[str, Any],
    chat_history: Optional[List[Dict[str, str]]] = None,
    orchestrator: Optional[Any] = None
) -> str:
    """
    Context Window Builder:
    Constructs unified context prompt containing attached file context, stored vision outputs, and user query.
    Registers precise context provenance entries in AgentOrchestrator.
    """
    if not attachment_res.get("resolved"):
        if orchestrator and chat_history:
            orchestrator.add_context_source(
                source="conversation",
                type="conversation_context",
                content_summary=f"Previous chat messages: {len(chat_history)}"
            )
        return user_query

    filename = attachment_res.get("filename", "Attached File")
    doc_text = attachment_res.get("text", "")
    vis_content = attachment_res.get("visual_content", [])
    overall_analysis = attachment_res.get("analysis")

    blocks = [f"--- ATTACHED FILE CONTEXT ({filename}) ---"]
    if doc_text:
        blocks.append(doc_text)
    
    if vis_content and not ("Visual Content Analysis" in doc_text):
        vis_lines = [f"- Page/Item {v.get('page', i+1)} ({v.get('type')}): {v.get('analysis')}" for i, v in enumerate(vis_content)]
        blocks.append("\n### Stored Visual Content Analysis (Qwen2.5-VL-3B):\n" + "\n".join(vis_lines))
    elif overall_analysis and not (overall_analysis in doc_text):
        blocks.append(f"\n### Image Analysis (Qwen2.5-VL-3B):\n{overall_analysis}")

    blocks.append("--- END ATTACHED FILE CONTEXT ---")
    blocks.append(f"\nUser Prompt:\n{user_query}")

    unified_prompt = "\n".join(blocks)

    if orchestrator:
        orchestrator.add_context_source(
            source="attachment_resolver",
            type="attached_file_context",
            content_summary=f"Attachment: '{filename}' ({len(doc_text)} chars text)"
        )
        orchestrator.add_context_source(
            source="document_processor",
            type="document_context",
            content_summary=f"Document text ({len(doc_text)} chars)"
        )
        if vis_content or overall_analysis:
            orchestrator.add_context_source(
                source="Qwen2.5-VL-3B",
                type="vision_analysis",
                content_summary=f"Vision analysis ({len(vis_content)} items)"
            )
        if chat_history:
            orchestrator.add_context_source(
                source="conversation",
                type="conversation_context",
                content_summary=f"Chat history ({len(chat_history)} messages)"
            )

    return unified_prompt
