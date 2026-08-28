import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class TraceStep(BaseModel):
    step_id: str = Field(..., description="Unique ID for this trace step")
    type: str = Field(..., description="Step type: tool, model, router, context, lifecycle, action, observation")
    component: str = Field(..., description="Executing component name")
    model: Optional[str] = Field(None, description="Associated AI model name if applicable")
    action: str = Field(..., description="Action performed by component")
    status: str = Field("started", description="Status: started, completed, failed")
    started_at: float = Field(default_factory=time.time, description="Timestamp step started")
    completed_at: Optional[float] = Field(None, description="Timestamp step completed")
    duration_ms: float = Field(0.0, description="Exact duration in milliseconds")
    input_summary: str = Field("", description="Safe non-sensitive input summary")
    output_summary: str = Field("", description="Safe output summary")
    output_available: bool = Field(False, description="Flag indicating output payload exists")
    vram_before_mb: Optional[float] = Field(None, description="GPU VRAM used before step")
    vram_after_mb: Optional[float] = Field(None, description="GPU VRAM used after step")
    passed_to: Optional[str] = Field(None, description="Target component output was passed to")
    error: Optional[str] = Field(None, description="Error message if step failed")

class ContextSource(BaseModel):
    source: str = Field(..., description="Origin component (e.g. Qwen2.5-VL-3B, document_processor)")
    type: str = Field(..., description="Context type (e.g. vision_analysis, extracted_text, user_prompt)")
    content_summary: str = Field(..., description="Summary preview of context content")
    timestamp: float = Field(default_factory=time.time)

class AgentExecutionTrace(BaseModel):
    request_id: str = Field(..., description="Unique request ID")
    chat_id: Optional[str] = Field(None, description="Target chat session ID")
    steps: List[TraceStep] = Field(default_factory=list, description="Ordered timeline of trace steps")
    context_sources: List[ContextSource] = Field(default_factory=list, description="Provenance sources fed into final model")
    final_generator: str = Field("", description="Display name of model that generated final response")
    final_model_id: str = Field("", description="Model ID of final generator")
    is_final_generator_vision: bool = Field(False, description="True if vision model directly generated final response")
    timing_summary: Dict[str, float] = Field(default_factory=dict, description="Timing metrics breakdown in ms")
    vram_summary: Dict[str, Any] = Field(default_factory=dict, description="VRAM telemetry metrics")
