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

def is_router_model(model_name: str) -> bool:
    """Returns True if the model name corresponds to the Query Router (qwen2.5:1.5b)."""
    if not model_name:
        return False
    name_lower = str(model_name).lower().strip()
    return "1.5b" in name_lower or "router" in name_lower or "qwen2.5:1.5" in name_lower

def is_model_protected(model_name: str) -> bool:
    """Returns True if the model is currently protected from unloading."""
    return MULTI_MODEL_MODE and is_router_model(model_name)

def can_auto_unload(model_name: str) -> bool:
    """
    Absolute Router & Generation Protection Check:
    Returns False if Multi-Model Mode is ENABLED and model is the Query Router (qwen2.5:1.5b).
    Returns True otherwise for automatic memory management / eviction.
    """
    if not model_name:
        return True
    if MULTI_MODEL_MODE and is_router_model(model_name):
        return False
    return True

def get_evictable_models(loaded_models: list) -> list:
    """
    Returns list of loaded models that are eligible for automatic eviction/unloading.
    Excludes protected Query Router model (qwen2.5:1.5b) when Multi-Model Mode is enabled.
    """
    return [
        m for m in loaded_models
        if can_auto_unload(m.get("name", m.get("model", "")))
    ]

def get_unload_candidates(loaded_models: list) -> list:
    """Alias for get_evictable_models."""
    return get_evictable_models(loaded_models)

def get_multi_model_mode() -> bool:
    """Returns current Multi-Model Mode status (True = ON, False = OFF)."""
    return MULTI_MODEL_MODE

def set_multi_model_mode(enabled: bool) -> Dict[str, Any]:
    """
    Sets Multi-Model Mode ON or OFF.
    When set to ON:
    - Automatically loads qwen2.5:1.5b Query Router into RAM/VRAM.
    - Evicts idle/LRU non-router task models if RAM/VRAM is tight.
    - Verifies router is loaded through Ollama.
    - If loading fails, reverts MULTI_MODEL_MODE = False and returns success=False.
    When set to OFF:
    - Removes router protection.
    - Automatically unloads qwen2.5:1.5b router from VRAM if loaded.
    """
    global MULTI_MODEL_MODE

    if enabled:
        # Temporarily enable flag so router load and safety checks evaluate protection
        MULTI_MODEL_MODE = True
        router_loaded, msg = ensure_router_loaded()
        if not router_loaded:
            # Revert mode to False on failure
            MULTI_MODEL_MODE = False
            return {
                "success": False,
                "multi_model_enabled": False,
                "error": f"Unable to load Query Router while preserving RAM/VRAM safety limits: {msg}"
            }
        return {
            "success": True,
            "multi_model_enabled": True,
            "router": {
                "name": ROUTER_MODEL_ID,
                "loaded": True,
                "protected": True
            },
            "ram_safety_reserve_mb": RAM_SAFETY_RESERVE_MB,
            "vram_safety_reserve_mb": VRAM_SAFETY_RESERVE_MB
        }
    else:
        MULTI_MODEL_MODE = False
        unloaded_router = False
        loaded_list = get_loaded_models()
        for m in loaded_list:
            model_name = m.get("name", "")
            if is_router_model(model_name):
                unload_model_and_verify(model_name, force=True)
                unloaded_router = True

        return {
            "success": True,
            "multi_model_enabled": False,
            "router_unloaded": unloaded_router,
            "ram_safety_reserve_mb": RAM_SAFETY_RESERVE_MB,
            "vram_safety_reserve_mb": VRAM_SAFETY_RESERVE_MB
        }

def ensure_router_loaded() -> Tuple[bool, str]:
    """
    Ensures Query Router (qwen2.5:1.5b) is loaded into RAM/VRAM for Multi-Model Mode:
    1. Checks if qwen2.5:1.5b is already loaded in Ollama.
    2. Verifies resource safety (RAM remaining after load >= 1GB, VRAM remaining after load >= 500MB).
    3. If memory is tight, evicts non-router task models (idle/LRU).
    4. Triggers load_model(ROUTER_MODEL_ID) and polls Ollama /api/ps to confirm load status.
    """
    import time
    loaded_list = get_loaded_models()
    is_router_loaded = any(is_router_model(m.get("name", "")) for m in loaded_list)
    if is_router_loaded:
        return True, f"Router ({ROUTER_MODEL_ID}) is already loaded in RAM/VRAM."

    # Check resource safety for router
    is_safe, msg, _ = check_resource_safety(ROUTER_MODEL_ID)
    if not is_safe:
        # Retrieve evictable non-router task models
        candidates = get_evictable_models(loaded_list)
        for m in candidates:
            m_name = m.get("name", "")
            print(f"[RESOURCES] Unloading non-router model '{m_name}' to free resources for Query Router...")
            unload_model_and_verify(m_name, force=True)
            time.sleep(0.5)
            # Re-check safety after each unload
            is_safe, _, _ = check_resource_safety(ROUTER_MODEL_ID)
            if is_safe:
                break

    # Re-verify resource safety after non-router eviction
    is_safe, msg, _ = check_resource_safety(ROUTER_MODEL_ID)
    if not is_safe:
        return False, f"Insufficient memory to load Query Router while preserving safety reserves. {msg}"

    # Load router model into Ollama
    load_success = load_model(ROUTER_MODEL_ID)
    if load_success:
        # Poll Ollama /api/ps up to 10 seconds to confirm router is loaded
        start = time.time()
        while (time.time() - start) < 10.0:
            time.sleep(0.5)
            curr_loaded = get_loaded_models()
            if any(is_router_model(m.get("name", "")) for m in curr_loaded):
                return True, f"Router ({ROUTER_MODEL_ID}) loaded successfully into memory."

    return False, f"Failed to verify router model ({ROUTER_MODEL_ID}) loading in memory."

def ensure_specialist_loaded(target_model_id: str) -> Tuple[bool, str]:
    """
    Model Loading & Protected Eviction Algorithm:
    STEP 1: Check if requested specialist model is already loaded. Use immediately if loaded.
    STEP 2: Check RAM (>= 1GB) and VRAM (>= 500MB) safety reserves. If safe, load model.
    STEP 3 & 4: If insufficient resources, retrieve unloadable non-router models ONLY.
                The protected Query Router (qwen2.5:1.5b) is strictly excluded.
    STEP 5: Evict non-router models iteratively using LRU order until resources are sufficient.
    EMERGENCY CASE: If only the router remains loaded and resources remain insufficient,
                    DO NOT unload the router. Keep router loaded and return clear status.
    """
    import time
    target_clean = target_model_id.lower().strip()
    loaded_list = get_loaded_models()

    # STEP 1: Check if target specialist model is already loaded
    is_target_loaded = any(target_clean in m.get("name", "").lower() for m in loaded_list)
    if is_target_loaded:
        return True, f"Specialist model {target_model_id} is already loaded."

    # STEP 2 & 3: Check resource safety before attempting eviction
    is_safe, msg, _ = check_resource_safety(target_model_id)
    if is_safe:
        load_success = load_model(target_model_id)
        if load_success:
            time.sleep(0.5)
            return True, f"Specialist model {target_model_id} loaded successfully."
        return False, f"Failed to load specialist model {target_model_id}."

    # STEP 4: Retrieve unloadable candidates (router is strictly excluded when Multi-Model Mode is ON)
    unload_candidates = get_unload_candidates(loaded_list)
    unloadable_candidates = [m for m in unload_candidates if not (target_clean in m.get("name", "").lower())]

    # EMERGENCY CASE: If no non-router models can be unloaded, do NOT unload router
    if not unloadable_candidates:
        return False, f"Insufficient resources to load {target_model_id}. The Query Router is protected while Multi-Model Mode is enabled."

    # STEP 5: Iteratively unload non-router models until safety thresholds are satisfied
    for m in unloadable_candidates:
        m_name = m.get("name", "")
        print(f"[RESOURCES] Unloading non-protected model '{m_name}' to free resources for {target_model_id}...")
        unload_model_and_verify(m_name)
        time.sleep(0.5)

        # Check if resources are now sufficient
        is_safe, _, _ = check_resource_safety(target_model_id)
        if is_safe:
            break

    # Re-verify resource safety after candidate eviction
    is_safe, msg, _ = check_resource_safety(target_model_id)
    if is_safe:
        load_success = load_model(target_model_id)
        if load_success:
            time.sleep(0.5)
            return True, f"Specialist model {target_model_id} loaded successfully."
        return False, f"Failed to load specialist model {target_model_id}."

    # Emergency protection trigger: Keep router loaded and return protected router error status
    return False, f"Insufficient resources to load {target_model_id}. The Query Router is protected while Multi-Model Mode is enabled."

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
    Prioritizes USER INTENT over document subject matter.
    Priority: DOCUMENT > RAG > CODING > REASONING > GENERAL
    """
    text = user_text.lower().strip()

    # 1. DOCUMENT INTENT - Check if user is asking about document content, names, topics, or summary
    doc_keywords = [
        "pdf", "docx", "file", "document", "summarize", "summary", "student name", "roll number",
        "author", "mentioned in", "described in", "topic", "page", "what is this document", "functions mentioned"
    ]
    if any(k in text for k in doc_keywords):
        # Unless user explicitly asks to write or debug code, treat as DOCUMENT
        if not any(k in text for k in ["write code", "fix code", "debug", "write a python program", "write script"]):
            return "DOCUMENT"

    # 2. RAG
    if any(k in text for k in ["according to our", "knowledge base", "rag database", "search database", "retrieve context"]):
        return "RAG"

    # 3. CODING - Requires explicit coding request (write, create, fix, debug, explain code)
    if any(k in text for k in ["write code", "fix code", "debug", "refactor code", "write python", "syntax error", "build api"]):
        return "CODING"
    if re.search(r'\b(write|create|generate|fix|debug)\s+(a\s+)?(python|js|script|code|program)\b', text):
        return "CODING"

    # 4. REASONING - math calculations, equations, or numbers with arithmetic operators (+, -, *, x, /, ×)
    if re.search(r'\b(math|calculate|equation|algebra|solve|proof)\b', text) or re.search(r'\d+\s*[\+\-\*\×x\/]\s*\d+', text):
        return "REASONING"

    # 5. DEFAULT GENERAL
    return "GENERAL"

def classify_query(user_text: str, orchestrator: Optional[Any] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Calls Qwen2.5 1.5B Router to classify query into exactly one route:
    DOCUMENT, RAG, CODING, REASONING, or GENERAL.
    Returns (normalized_route, router_info).
    """
    step_r = None
    if orchestrator:
        from agent.trace_events import summarize_text
        step_r = orchestrator.start_step(
            type="router",
            component="router",
            model=ROUTER_MODEL_ID,
            action="route_classification",
            input_summary=f"User Query: '{summarize_text(user_text, 70)}'",
            passed_to="Target Model"
        )

    prompt = f"""You are an intent routing classifier for an AI application.
Your ONLY task is to classify the user query into EXACTLY ONE of these 5 categories:

- GENERAL: Explanations, general knowledge, concepts, science, comparisons, overview questions, or everyday conversational queries.
- CODING: Software development, writing or fixing code, programming languages (Python, JS, HTML, etc.), API endpoints, debugging, syntax, or algorithms.
- REASONING: Mathematical calculations, math equations, logic puzzles, or formal step-by-step arithmetic.
- DOCUMENT: Reading, analyzing, extracting information, or asking about the content/topics of an uploaded document, PDF, or text file.
- RAG: Retrieving information from local knowledge bases, internal databases, or specific local vector stores.

CRITICAL INSTRUCTIONS:
- Classify based strictly on USER INTENT, NOT document subject.
- DOCUMENT: Questions asking about the content, text, student names, roll numbers, data, functions, or topics inside an uploaded document/PDF/file (EVEN IF the document contains Python, Pandas, or programming code!).
- CODING: ONLY when the user explicitly requests WRITING, GENERATING, DEBUGGING, FIXING, or REFACTORING code (e.g., "Write a Python script", "Fix this bug"). Questions asking "What is the student name?" or "What are the NumPy functions in the file?" are DOCUMENT tasks, NOT CODING tasks.

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

            if step_r and orchestrator:
                target_info = ROUTE_MODEL_MAP.get(norm_route, {})
                orchestrator.complete_step(
                    step_r,
                    output_summary=f"Route: {norm_route} -> Model: {target_info.get('name', 'Phi-4 Mini')}",
                    passed_to=target_info.get('name', 'Phi-4 Mini')
                )

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

    if step_r and orchestrator:
        target_info = ROUTE_MODEL_MAP.get(norm_route, {})
        orchestrator.fail_step(
            step_r,
            error_message=raw_output,
            fallback_action=f"Priority Keyword Router -> {norm_route}"
        )

    return norm_route, {
        "method": "fallback_priority_router",
        "raw_output": raw_output or "LLM Router unavailable/invalid. Applied priority rule.",
        "route": norm_route
    }

