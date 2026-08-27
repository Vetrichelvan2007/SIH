"""
Services package for Sovereign AI Workbench.
Encapsulates system telemetry monitoring, Ollama API interactions, and model lifecycle management.
"""
from .system_monitor import get_system_status
from .ollama_service import get_loaded_models, load_model, unload_model
from .model_manager import switch_model_stream
from .router_service import (
    get_multi_model_mode,
    set_multi_model_mode,
    check_resource_safety,
    classify_query,
    ROUTE_MODEL_MAP,
    ROUTE_PRIORITY,
    VALID_ROUTES
)

__all__ = [
    "get_system_status",
    "get_loaded_models",
    "load_model",
    "unload_model",
    "switch_model_stream",
    "get_multi_model_mode",
    "set_multi_model_mode",
    "check_resource_safety",
    "classify_query",
    "ROUTE_MODEL_MAP",
    "ROUTE_PRIORITY",
    "VALID_ROUTES"
]

