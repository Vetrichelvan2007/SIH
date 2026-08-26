"""
Services package for Sovereign AI Workbench.
Encapsulates system telemetry monitoring, Ollama API interactions, and model lifecycle management.
"""
from .system_monitor import get_system_status
from .ollama_service import get_loaded_models, load_model, unload_model
from .model_manager import switch_model_stream

__all__ = [
    "get_system_status",
    "get_loaded_models",
    "load_model",
    "unload_model",
    "switch_model_stream",
]
