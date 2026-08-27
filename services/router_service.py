import json
import re
import requests
import psutil
from typing import Tuple, Dict, Any, Optional
from .system_monitor import get_gpu_info
from .ollama_service import get_loaded_models, unload_model, load_model, unload_model_and_verify

# Configurable Global State for Multi-Model Mode
MULTI_MODEL_MODE: bool = False

# Default Router Model
ROUTER_MODEL_ID: str = "qwen2.5:1.5b"

# Configurable Resource Safety Reserves (in MB)
RAM_SAFETY_RESERVE_MB: float = 1024.0   # Default 1 GB
VRAM_SAFETY_RESERVE_MB: float = 500.0   # Default 500 MB

# Estimated Memory requirements (in MB) when model is not yet loaded
ESTIMATED_MODEL_RAM_MB: Dict[str, float] = {
    "qwen2.5:1.5b": 1100.0,
    "qwen2.5-coder": 4000.0,
    "phi4-mini": 3000.0,
    "default": 3000.0
}

# Strict Priority Order: DOCUMENT > RAG > CODING > REASONING > GENERAL
VALID_ROUTES = ["DOCUMENT", "RAG", "CODING", "REASONING", "GENERAL"]
ROUTE_PRIORITY = {
    "DOCUMENT": 1,
    "RAG": 2,
    "CODING": 3,
    "REASONING": 4,
    "GENERAL": 5
}

# Route to Specialist Model Mapping
ROUTE_MODEL_MAP = {
    "DOCUMENT": {"id": "phi4-mini", "name": "Phi-4 Mini", "task": "question"},
    "RAG": {"id": "phi4-mini", "name": "Phi-4 Mini", "task": "question"},
    "CODING": {"id": "qwen2.5-coder", "name": "Qwen2.5-Coder", "task": "coding"},
    "REASONING": {"id": "phi4-mini", "name": "Phi-4 Mini", "task": "question"},
    "GENERAL": {"id": "phi4-mini", "name": "Phi-4 Mini", "task": "question"}
}

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

def get_multi_model_mode() -> bool:
    """Returns current Multi-Model Mode status (True = ON, False = OFF)."""
    return MULTI_MODEL_MODE

def set_multi_model_mode(enabled: bool) -> Dict[str, Any]:
    """
    Sets Multi-Model Mode ON or OFF.
    When set to OFF:
    - Automatically unloads qwen2.5:1.5b router from VRAM if loaded.
    - Releases RAM and VRAM resources.
    """
    global MULTI_MODEL_MODE
    MULTI_MODEL_MODE = bool(enabled)

    unloaded_router = False
    if not MULTI_MODEL_MODE:
        # Check if router model is in loaded models list and unload it
        loaded_list = get_loaded_models()
        for m in loaded_list:
            model_name = m.get("name", "").lower()
            if "qwen2.5:1.5b" in model_name or "qwen2.5:1.5" in model_name or "1.5b" in model_name:
                unload_model_and_verify(m.get("name", ROUTER_MODEL_ID))
                unloaded_router = True

    return {
        "multi_model_mode": MULTI_MODEL_MODE,
        "router_unloaded": unloaded_router,
        "ram_safety_reserve_mb": RAM_SAFETY_RESERVE_MB,
        "vram_safety_reserve_mb": VRAM_SAFETY_RESERVE_MB
    }

def ensure_router_loaded() -> Tuple[bool, str]:
    """
    Step 1 & 2 of Multi-Model Mode memory workflow:
    - Checks if qwen2.5:1.5b router is already loaded.
    - If not loaded, verifies resource safety (RAM >= 1GB, VRAM >= safety reserve).
    - If memory is insufficient, gracefully unloads currently loaded inference model(s)
      and waits until RAM/VRAM resources are actually released before loading qwen2.5:1.5b.
    """
    import time
    loaded_list = get_loaded_models()
    is_router_loaded = any("1.5b" in m.get("name", "").lower() or "router" in m.get("name", "").lower() for m in loaded_list)
    if is_router_loaded:
        return True, "Router (qwen2.5:1.5b) is already loaded in RAM/VRAM."

    # Check resource safety for router
    is_safe, msg, _ = check_resource_safety(ROUTER_MODEL_ID)
    if not is_safe:
        # Unload non-router models to free VRAM/RAM
        for m in loaded_list:
            m_name = m.get("name", "")
            if not ("1.5b" in m_name.lower() or "router" in m_name.lower()):
                unload_model_and_verify(m_name)
        time.sleep(0.5)

    # Load router model
    load_success = load_model(ROUTER_MODEL_ID)
    if load_success:
        time.sleep(0.5)
        return True, "Router (qwen2.5:1.5b) loaded successfully."
    return False, "Failed to load router model into memory."

def ensure_specialist_loaded(target_model_id: str) -> Tuple[bool, str]:
    """
    Step 4 & 5 of Multi-Model Mode memory workflow:
    - Checks if target specialist model (e.g., qwen2.5-coder or phi4-mini) is already loaded.
    - If not loaded, checks available RAM & VRAM safety.
    - If memory is insufficient to keep both router and specialist loaded, unloads qwen2.5:1.5b
      router model and waits for memory release before loading the specialist model.
    """
    import time
    target_clean = target_model_id.lower().strip()
    loaded_list = get_loaded_models()
    is_target_loaded = any(target_clean in m.get("name", "").lower() for m in loaded_list)
    if is_target_loaded:
        return True, f"Specialist model {target_model_id} is already loaded."

    # Check resource safety
    is_safe, msg, _ = check_resource_safety(target_model_id)
    if not is_safe:
        # Unload router model (or idle models) to free RAM & VRAM for the specialist model
        for m in loaded_list:
            m_name = m.get("name", "")
            if not (target_clean in m_name.lower()):
                unload_model_and_verify(m_name)
        time.sleep(0.5)

    load_success = load_model(target_model_id)
    if load_success:
        time.sleep(0.5)
        return True, f"Specialist model {target_model_id} loaded successfully."
    return False, f"Failed to load specialist model {target_model_id}."

def update_safety_reserves(ram_reserve_mb: Optional[float] = None, vram_reserve_mb: Optional[float] = None) -> Dict[str, Any]:
    """Updates RAM and VRAM safety reserve thresholds."""
    global RAM_SAFETY_RESERVE_MB, VRAM_SAFETY_RESERVE_MB
    if ram_reserve_mb is not None and ram_reserve_mb >= 0:
        RAM_SAFETY_RESERVE_MB = float(ram_reserve_mb)
    if vram_reserve_mb is not None and vram_reserve_mb >= 0:
        VRAM_SAFETY_RESERVE_MB = float(vram_reserve_mb)
    return {
        "ram_safety_reserve_mb": RAM_SAFETY_RESERVE_MB,
        "vram_safety_reserve_mb": VRAM_SAFETY_RESERVE_MB
    }

def check_resource_safety(target_model_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verifies system RAM and GPU VRAM availability before loading a model.
    Conditions:
    1. available_RAM_after_loading >= 1 GB (RAM_SAFETY_RESERVE_MB)
    2. available_VRAM_after_loading >= 500 MB (VRAM_SAFETY_RESERVE_MB)
    
    Returns (is_safe, message, metrics).
    """
    # Check currently loaded models
    loaded_list = get_loaded_models()
    loaded_names = [m.get("name", "").lower() for m in loaded_list]
    target_clean = target_model_id.lower().strip()

    # If target model is already loaded in VRAM, no additional memory is required to load it
    is_already_loaded = any(target_clean in name for name in loaded_names)

    est_ram_mb = 0.0 if is_already_loaded else ESTIMATED_MODEL_RAM_MB.get(target_clean, ESTIMATED_MODEL_RAM_MB["default"])
    est_vram_mb = 0.0 if is_already_loaded else ESTIMATED_MODEL_RAM_MB.get(target_clean, ESTIMATED_MODEL_RAM_MB["default"])

    # 1. System RAM Check
    mem = psutil.virtual_memory()
    avail_ram_mb = mem.available / (1024 * 1024)
    ram_after_loading_mb = avail_ram_mb - est_ram_mb
    is_ram_safe = ram_after_loading_mb >= RAM_SAFETY_RESERVE_MB

    # 2. GPU VRAM Check
    gpu_info = get_gpu_info()
    if gpu_info.get("available", False):
        vram_total_mb = gpu_info.get("vram_total_mb", 0)
        vram_used_mb = gpu_info.get("vram_used_mb", 0)
        avail_vram_mb = max(0, vram_total_mb - vram_used_mb)
        vram_after_loading_mb = avail_vram_mb - est_vram_mb
        is_vram_safe = vram_after_loading_mb >= VRAM_SAFETY_RESERVE_MB
    else:
        # GPU not detected; VRAM constraint passed gracefully (CPU offload fallback)
        avail_vram_mb = 999999.0
        vram_after_loading_mb = 999999.0
        is_vram_safe = True

    is_both_safe = is_ram_safe and is_vram_safe

    metrics = {
        "target_model": target_model_id,
        "is_already_loaded": is_already_loaded,
        "avail_ram_mb": round(avail_ram_mb, 1),
        "ram_after_loading_mb": round(ram_after_loading_mb, 1),
        "ram_reserve_mb": RAM_SAFETY_RESERVE_MB,
        "is_ram_safe": is_ram_safe,
        "avail_vram_mb": round(avail_vram_mb, 1) if gpu_info.get("available") else "N/A",
        "vram_after_loading_mb": round(vram_after_loading_mb, 1) if gpu_info.get("available") else "N/A",
        "vram_reserve_mb": VRAM_SAFETY_RESERVE_MB,
        "is_vram_safe": is_vram_safe,
        "is_safe": is_both_safe
    }

    if is_both_safe:
        msg = f"Resource check passed: RAM after load ({round(ram_after_loading_mb/1024, 2)} GB >= {round(RAM_SAFETY_RESERVE_MB/1024, 2)} GB), VRAM safe."
    elif not is_ram_safe:
        msg = f"Insufficient System RAM reserve. Available after load: {round(ram_after_loading_mb/1024, 2)} GB < required {round(RAM_SAFETY_RESERVE_MB/1024, 2)} GB reserve."
    else:
        msg = f"Insufficient GPU VRAM reserve. Available after load: {round(vram_after_loading_mb, 1)} MB < required {VRAM_SAFETY_RESERVE_MB} MB reserve."

    return is_both_safe, msg, metrics

def normalize_route(raw_output: str) -> str:
    """
    Safely extracts and normalizes the route from raw LLM or router output.
    Handles formats:
    - CODING / coding / "CODING" / CODING\n
    - LABEL: CODING
    - {"route": "CODING"}
    - ```json {"route": "CODING"} ```
    Returns one of: CODING, GENERAL, REASONING, RAG, DOCUMENT. Defaults to GENERAL.
    """
    if not raw_output or not isinstance(raw_output, str):
        return "GENERAL"

    cleaned = raw_output.replace("```json", "").replace("```", "").strip()

    # 1. Check JSON route format: {"route": "..."}
    json_match = re.search(r'\{\s*"route"\s*:\s*"([A-Za-z_]+)"\s*\}', cleaned, re.IGNORECASE)
    if json_match:
        cand = json_match.group(1).upper()
        if cand in VALID_ROUTES:
            return cand

    # 2. Check general JSON parse
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "route" in data:
            cand = str(data["route"]).strip().upper()
            if cand in VALID_ROUTES:
                return cand
    except Exception:
        pass

    # 3. Direct route word boundary match in uppercase text
    upper_cleaned = cleaned.upper()
    for valid in ["DOCUMENT", "RAG", "CODING", "REASONING", "GENERAL"]:
        if re.search(r'\b' + valid + r'\b', upper_cleaned):
            return valid

    return "GENERAL"

def fallback_keyword_routing(user_text: str) -> str:
    """
    Strict priority keyword router used if router LLM fails or returns unparseable route.
    Priority: DOCUMENT > RAG > CODING > REASONING > GENERAL
    """
    text = user_text.lower().strip()

    # 1. DOCUMENT
    if any(k in text for k in ["pdf", "docx", "summarize document", "uploaded pdf", "file content", "read document"]):
        return "DOCUMENT"

    # 2. RAG
    if any(k in text for k in ["according to our", "knowledge base", "rag database", "search database", "retrieve context"]):
        return "RAG"

    # 3. CODING - specific coding keywords only; avoid generic words like "program", "system", "ram", "model"
    coding_keywords = [
        "fastapi", "react", "python", "javascript", "typescript", "html", "css", "sql",
        "write code", "fix code", "coding", "syntax error", "refactor code", "endpoint",
        "quicksort", "function ", "def ", "const ", "let ", "var ", "import ", "return ",
        "class ", "algorithm"
    ]
    if any(k in text for k in coding_keywords) or re.search(r'\b(code|bug|fix|script|react|vue|node)\b', text):
        return "CODING"

    # 4. REASONING - math calculations, equations, or numbers with arithmetic operators (+, -, *, x, /, ×)
    if re.search(r'\b(math|calculate|equation|algebra|solve|proof)\b', text) or re.search(r'\d+\s*[\+\-\*\×x\/]\s*\d+', text):
        return "REASONING"

    # 5. DEFAULT GENERAL
    return "GENERAL"

def classify_query(user_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Calls Qwen2.5 1.5B Router to classify query into exactly one route:
    DOCUMENT, RAG, CODING, REASONING, or GENERAL.
    Returns (normalized_route, router_info).
    """
    prompt = f"""You are an intent routing classifier for an AI application.
Your ONLY task is to classify the user query into EXACTLY ONE of these 5 categories:

- GENERAL: Explanations, general knowledge, concepts, science, comparisons, overview questions, or everyday conversational queries.
- CODING: Software development, writing or fixing code, programming languages (Python, JS, HTML, etc.), API endpoints, debugging, syntax, or algorithms.
- REASONING: Mathematical calculations, math equations, logic puzzles, or formal step-by-step arithmetic.
- DOCUMENT: Analyzing, reading, or summarizing uploaded documents, PDFs, or text files.
- RAG: Retrieving information from local knowledge bases, internal databases, or specific local vector stores.

CRITICAL INSTRUCTIONS:
- Concept explanations, comparisons (e.g. CPU, RAM vs VRAM, photosynthesis, how things work) MUST be classified as GENERAL.
- Programming/code writing MUST be classified as CODING.

Return valid JSON ONLY:
{{"route": "CATEGORY_NAME"}}

User Query:
{user_text}"""

    payload = {
        "model": ROUTER_MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }

    raw_output = ""
    try:
        res = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=10)
        if res.status_code == 200:
            raw_output = res.json().get("message", {}).get("content", "").strip()
            norm_route = normalize_route(raw_output)
            return norm_route, {
                "method": "qwen2.5:1.5b_router",
                "raw_output": raw_output,
                "route": norm_route
            }
    except Exception as exc:
        raw_output = f"Router LLM Error: {exc}"

    # Fallback to priority keyword router if router LLM fails
    fallback_route = fallback_keyword_routing(user_text)
    norm_route = normalize_route(fallback_route)
    return norm_route, {
        "method": "fallback_priority_router",
        "raw_output": raw_output or "LLM Router unavailable/invalid. Applied priority rule.",
        "route": norm_route
    }
