import time
import uuid
from typing import Optional, List, Dict, Any

from .execution_trace import TraceStep, ContextSource, AgentExecutionTrace
from services.system_monitor import get_gpu_info

class AgentOrchestrator:
    """
    Central Agent Execution Tracker & Orchestrator:
    Empirically records steps, timers, VRAM deltas, context flow provenance, and model attributions.
    """
    def __init__(self, request_id: Optional[str] = None, chat_id: Optional[str] = None):
        self.request_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
        self.chat_id = chat_id
        self.step_counter = 0
        self.start_time = time.perf_counter()
        
        self.steps: Dict[str, TraceStep] = {}
        self.step_order: List[str] = []
        self.context_sources: List[ContextSource] = []
        
        self.final_generator_name: str = ""
        self.final_generator_id: str = ""
        self.is_final_generator_vision: bool = False

    def _get_current_vram_mb(self) -> Optional[float]:
        try:
            gpu = get_gpu_info()
            if gpu.get("available"):
                return float(gpu.get("vram_used_mb", 0))
        except Exception:
            pass
        return None

    def start_step(
        self,
        type: str,
        component: str,
        action: str,
        model: Optional[str] = None,
        input_summary: str = "",
        passed_to: Optional[str] = None
    ) -> str:
        """
        Starts tracking an execution step. Returns unique step_id.
        """
        self.step_counter += 1
        step_id = f"step_{self.step_counter:02d}"
        vram_before = self._get_current_vram_mb()

        step = TraceStep(
            step_id=step_id,
            type=type,
            component=component,
            model=model,
            action=action,
            status="started",
            started_at=time.time(),
            input_summary=input_summary,
            vram_before_mb=vram_before,
            passed_to=passed_to
        )

        self.steps[step_id] = step
        self.step_order.append(step_id)
        return step_id

    def complete_step(
        self,
        step_id: str,
        output_summary: str = "",
        passed_to: Optional[str] = None
    ) -> None:
        """
        Marks an execution step as completed with exact duration and output summary.
        """
        if step_id not in self.steps:
            return

        step = self.steps[step_id]
        step.status = "completed"
        step.completed_at = time.time()
        step.duration_ms = round((step.completed_at - step.started_at) * 1000, 2)
        step.output_summary = output_summary
        step.output_available = bool(output_summary)
        step.vram_after_mb = self._get_current_vram_mb()
        if passed_to:
            step.passed_to = passed_to

    def fail_step(
        self,
        step_id: str,
        error_message: str,
        fallback_action: Optional[str] = None
    ) -> None:
        """
        Marks an execution step as failed, recording the error and optional fallback action.
        """
        if step_id not in self.steps:
            return

        step = self.steps[step_id]
        step.status = "failed"
        step.completed_at = time.time()
        step.duration_ms = round((step.completed_at - step.started_at) * 1000, 2)
        step.error = error_message
        step.output_summary = f"FAILED: {error_message}"
        if fallback_action:
            step.output_summary += f" -> Activated Fallback: {fallback_action}"
        step.vram_after_mb = self._get_current_vram_mb()

    def add_context_source(
        self,
        source: str,
        type: str,
        content_summary: str
    ) -> None:
        """
        Registers a context provenance source item fed into the LLM context window.
        """
        item = ContextSource(
            source=source,
            type=type,
            content_summary=content_summary,
            timestamp=time.time()
        )
        self.context_sources.append(item)

    def set_final_generator(
        self,
        model_name: str,
        model_id: str,
        is_vision: bool = False
    ) -> None:
        """
        Sets the model that actually generated the final user-visible response.
        """
        self.final_generator_name = model_name
        self.final_generator_id = model_id
        self.is_final_generator_vision = is_vision

    def build_trace(self) -> AgentExecutionTrace:
        """
        Compiles and returns full AgentExecutionTrace object with timing and VRAM metrics.
        """
        total_duration_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        
        timing = {"total_ms": total_duration_ms}
        for s_id in self.step_order:
            step = self.steps[s_id]
            comp_key = f"{step.component.lower()}_ms"
            timing[comp_key] = timing.get(comp_key, 0.0) + step.duration_ms

        ordered_steps = [self.steps[s_id] for s_id in self.step_order]

        gpu_info = get_gpu_info()

        return AgentExecutionTrace(
            request_id=self.request_id,
            chat_id=self.chat_id,
            steps=ordered_steps,
            context_sources=self.context_sources,
            final_generator=self.final_generator_name or "Phi-4 Mini",
            final_model_id=self.final_generator_id or "phi4-mini",
            is_final_generator_vision=self.is_final_generator_vision,
            timing_summary=timing,
            vram_summary={
                "available": gpu_info.get("available", False),
                "gpu_name": gpu_info.get("name"),
                "vram_used_mb": gpu_info.get("vram_used_mb", 0),
                "vram_total_mb": gpu_info.get("vram_total_mb", 0)
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns JSON-serializable dictionary representation of the trace.
        """
        return self.build_trace().model_dump()
