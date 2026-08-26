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

def unload_model(model_name: str) -> bool:
    """
    Instructs Ollama to unload a model immediately from VRAM using keep_alive: 0.
    """
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
