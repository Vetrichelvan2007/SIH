import requests

OLLAMA_PS_URL = "http://localhost:11434/api/ps"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

def get_loaded_models() -> list:
    """
    Calls Ollama GET /api/ps to retrieve list of currently loaded models in VRAM.
    """
    try:
        res = requests.get(OLLAMA_PS_URL, timeout=3)
        if res.status_code == 200:
            return res.json().get("models", [])
    except Exception:
        pass
    return []

def unload_model(model_name: str, force: bool = False) -> bool:
    """
    Instructs Ollama to unload a model immediately from VRAM using keep_alive: 0.
    Blocks unload if Multi-Model Mode is enabled and model is the protected Query Router, unless force=True.
    """
    if not force:
        try:
            from services.router_service import can_auto_unload
            if not can_auto_unload(model_name):
                print(f"[PROTECTION NOTICE] Automatic unload blocked: '{model_name}' is protected while Multi-Model Mode is enabled.")
                return False
        except ImportError:
            pass

    try:
        # Request unload using keep_alive: 0
        payload = {
            "model": model_name,
            "keep_alive": 0
        }
        res = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def unload_model_and_verify(model_name: str, max_timeout_sec: float = 6.0, force: bool = False) -> bool:
    """
    Requests Ollama to unload a model and polls /api/ps until RAM/VRAM resources
    are confirmed released or until max_timeout_sec is reached.
    """
    import time
    if not model_name:
        return True

    if not force:
        try:
            from services.router_service import can_auto_unload
            if not can_auto_unload(model_name):
                print(f"[PROTECTION NOTICE] Automatic unload blocked: '{model_name}' is protected while Multi-Model Mode is enabled.")
                return False
        except ImportError:
            pass

    unload_model(model_name, force=force)
    model_name_clean = model_name.lower().strip()

    start = time.time()
    while (time.time() - start) < max_timeout_sec:
        time.sleep(0.5)
        loaded = get_loaded_models()
        still_loaded = any(model_name_clean in m.get("name", "").lower() for m in loaded)
        if not still_loaded:
            return True

    return False

def load_model(model_name: str) -> bool:
    """
    Triggers Ollama to load a model into VRAM using keep_alive: "1h".
    """
    try:
        payload = {
            "model": model_name,
            "keep_alive": "1h"
        }
        res = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=60)
        return res.status_code == 200
    except Exception:
        return False
