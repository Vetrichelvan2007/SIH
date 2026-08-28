import os
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from tools.documents.detector import detect_file_type
from tools.documents.document_router import route_and_process_document
from tools.images.image_processor import process_image
from tools.images.vision_router import should_trigger_vision
from services.ollama_service import (
    get_loaded_models,
    analyze_with_vision_model,
    unload_model_and_verify
)
from services.router_service import ensure_specialist_loaded
from agent.trace_events import summarize_text, summarize_vision_output

VISION_MODEL_ID = "qwen2.5vl:3b"

# Pydantic Response Schemas
class VisualContentItem(BaseModel):
    page: Optional[int] = None
    type: str = Field(..., description="Type of visual content: scanned_page, embedded_image, slide_image, or direct_image")
    analysis: Optional[str] = Field(None, description="Qwen2.5-VL-3B analysis output")

class ProcessingResult(BaseModel):
    file_type: str = Field(..., description="Extension or format: pdf, docx, pptx, xlsx, csv, image, txt, md")
    content_type: str = Field(..., description="Category: document, visual, structured")
    text: str = Field("", description="Extracted document text or Markdown content")
    visual_content: List[Dict[str, Any]] = Field(default_factory=list, description="Array of visual analysis items")
    analysis: Optional[str] = Field(None, description="Overall visual analysis summary if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata metrics: pages, rows, images count, etc.")

def process_uploaded_file(
    file_path: str,
    user_prompt: str = "",
    filename: Optional[str] = None,
    orchestrator: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Unified File Processing Workflow with Agent Orchestration Instrumentation:
    1. Detect file type & category (logged to trace).
    2. Route to specialized non-LLM document or image processor (logged to trace).
    3. Evaluate Vision Router decision (logged to trace).
    4. Dynamically manage Qwen2.5-VL-3B lifecycle in VRAM (logged to trace).
    5. Return unified ProcessingResult dictionary.
    """
    # 1. File Type Detection
    step_det = None
    if orchestrator:
        step_det = orchestrator.start_step(
            type="tool",
            component="detector",
            action="file_type_detection",
            input_summary=f"File: '{filename or os.path.basename(file_path)}'",
            passed_to="document_router"
        )

    detection = detect_file_type(file_path, filename=filename)
    file_type = detection["file_type"]
    content_type = detection["content_type"]
    name = detection["filename"]

    if step_det and orchestrator:
        orchestrator.complete_step(
            step_det,
            output_summary=f"Category: {content_type.upper()} | Type: {file_type.upper()}",
            passed_to="image_processor" if content_type == "visual" else "document_router"
        )

    if not detection["is_supported"]:
        if step_det and orchestrator:
            orchestrator.fail_step(step_det, f"Unsupported file format '.{file_type}'")
        raise ValueError(f"Unsupported file format '.{file_type}'. Supported: PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, JPG, PNG, WEBP.")

    visual_content_items = []
    overall_analysis = None
    extracted_text = ""

    # ==================================================
    # CASE 1: DIRECT IMAGE FILES
    # ==================================================
    if content_type == "visual" or file_type == "image":
        step_img = None
        if orchestrator:
            step_img = orchestrator.start_step(
                type="tool",
                component="image_processor",
                action="image_preprocessing",
                input_summary=f"Image: '{name}'",
                passed_to="Qwen2.5-VL-3B"
            )

        img_info = process_image(file_path, filename=name)
        b64_image = img_info["base64_image"]

        if step_img and orchestrator:
            orchestrator.complete_step(
                step_img,
                output_summary=f"Resized & encoded JPEG ({img_info['width']}x{img_info['height']}px)"
            )

        # Vision Model Analysis Step
        step_vis = None
        if orchestrator:
            step_vis = orchestrator.start_step(
                type="model",
                component="vision",
                model=VISION_MODEL_ID,
                action="image_analysis",
                input_summary=f"Image bytes + prompt: '{summarize_text(user_prompt or 'Analyze image', 60)}'",
                passed_to="Context Builder"
            )

        # Ensure Qwen2.5-VL-3B is loaded safely
        spec_loaded, spec_msg = ensure_specialist_loaded(VISION_MODEL_ID)

        vision_prompt = user_prompt or "Analyze this image in detail. Describe its main objects, structure, text, charts, or technical content."
        vision_analysis = analyze_with_vision_model(vision_prompt, [b64_image], model_name=VISION_MODEL_ID)

        is_error = "[Vision Processing Error" in vision_analysis

        if step_vis and orchestrator:
            if is_error:
                orchestrator.fail_step(step_vis, vision_analysis, fallback_action="Original prompt fallback")
            else:
                orchestrator.complete_step(step_vis, output_summary=summarize_vision_output(vision_analysis))

        if not is_error and orchestrator:
            orchestrator.add_context_source(
                source="Qwen2.5-VL-3B",
                type="vision_analysis",
                content_summary=summarize_vision_output(vision_analysis)
            )

        overall_analysis = vision_analysis
        extracted_text = f"[Image Analysis by Qwen2.5-VL-3B]\n{vision_analysis}"

        visual_content_items.append({
            "page": 1,
            "type": "direct_image",
            "analysis": vision_analysis
        })

        metadata = {
            "width": img_info["width"],
            "height": img_info["height"],
            "format": img_info["format"]
        }

    # ==================================================
    # CASE 2: DOCUMENTS & STRUCTURED FILES
    # ==================================================
    else:
        # Step 1: Extract non-LLM document text & visual candidates
        step_doc = None
        if orchestrator:
            step_doc = orchestrator.start_step(
                type="tool",
                component="document_router",
                action=f"{file_type.lower()}_extraction",
                input_summary=f"Document: '{name}' ({file_type.upper()})",
                passed_to="Vision Router"
            )

        doc_res = route_and_process_document(file_path, filename=name)
        extracted_text = doc_res["text"]
        raw_visual_items = doc_res.get("visual_items", [])
        metadata = doc_res.get("metadata", {})

        has_scanned = any(item.get("type") == "scanned_page" for item in raw_visual_items)
        embedded_count = len(raw_visual_items)

        if step_doc and orchestrator:
            orchestrator.complete_step(
                step_doc,
                output_summary=f"Extracted {len(extracted_text)} chars text, {embedded_count} visual candidates"
            )
            orchestrator.add_context_source(
                source="document_processor",
                type="extracted_text",
                content_summary=summarize_text(extracted_text, 100)
            )

        # Step 2: Check Vision Router recommendation
        step_vrouter = None
        if orchestrator:
            step_vrouter = orchestrator.start_step(
                type="router",
                component="vision_router",
                action="visual_processing_decision",
                input_summary=f"Scanned: {has_scanned}, Embedded items: {embedded_count}",
                passed_to="Qwen2.5-VL-3B" if (has_scanned or embedded_count > 0) else "Context Builder"
            )

        trigger_vision, vision_reason = should_trigger_vision(
            file_type=file_type,
            user_prompt=user_prompt,
            has_scanned_pages=has_scanned,
            embedded_visual_count=embedded_count
        )

        if step_vrouter and orchestrator:
            orchestrator.complete_step(
                step_vrouter,
                output_summary=f"Trigger Vision: {trigger_vision} ({vision_reason})"
            )

        # Step 3: Execute Qwen2.5-VL-3B ONLY if vision router recommends it and visual items exist
        if trigger_vision and raw_visual_items:
            print(f"[VISION ROUTER] {vision_reason}")
            
            step_vis = None
            if orchestrator:
                step_vis = orchestrator.start_step(
                    type="model",
                    component="vision",
                    model=VISION_MODEL_ID,
                    action="visual_pages_analysis",
                    input_summary=f"Processing {min(len(raw_visual_items), 5)} visual pages/images",
                    passed_to="Context Builder"
                )

            ensure_specialist_loaded(VISION_MODEL_ID)

            vis_summaries = []
            for item in raw_visual_items[:5]:  # Limit to max 5 visual pages/images
                b64_img = item.get("base64_image")
                page_num = item.get("page") or item.get("slide")
                item_type = item.get("type", "visual_item")

                item_prompt = f"Analyze page/image {page_num if page_num else ''} from document '{name}'. Describe key visual elements, charts, diagrams, or scanned text."
                item_analysis = analyze_with_vision_model(item_prompt, [b64_img], model_name=VISION_MODEL_ID)

                visual_content_items.append({
                    "page": page_num,
                    "type": item_type,
                    "analysis": item_analysis
                })
                vis_summaries.append(f"Page {page_num}: {summarize_text(item_analysis, 60)}")

            if step_vis and orchestrator:
                orchestrator.complete_step(
                    step_vis,
                    output_summary=f"Analyzed {len(visual_content_items)} items: {'; '.join(vis_summaries[:2])}"
                )
                orchestrator.add_context_source(
                    source="Qwen2.5-VL-3B",
                    type="visual_content_analysis",
                    content_summary=f"Analyzed {len(visual_content_items)} visual pages/charts"
                )

            # Append visual analysis summary to document context
            if visual_content_items:
                analysis_blocks = [f"- Page/Item {v.get('page', i+1)}: {v['analysis']}" for i, v in enumerate(visual_content_items)]
                extracted_text += "\n\n### Visual Content Analysis (Qwen2.5-VL-3B):\n" + "\n".join(analysis_blocks)

    result = ProcessingResult(
        file_type=file_type,
        content_type=content_type,
        text=extracted_text,
        visual_content=visual_content_items,
        analysis=overall_analysis,
        metadata=metadata
    )

    return result.model_dump()
