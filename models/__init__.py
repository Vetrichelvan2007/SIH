"""
Models package for Sovereign AI Workbench.
Encapsulates individual local model execution handlers.
"""
from .qwen_coder import generate_code_response, stream_code_response
from .phi_answer import generate_answer_response, stream_answer_response

__all__ = [
    "generate_code_response", 
    "stream_code_response", 
    "generate_answer_response", 
    "stream_answer_response"
]
