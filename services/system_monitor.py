import subprocess
import requests
import psutil

OLLAMA_PS_URL = "http://localhost:11434/api/ps"

def get_gpu_info() -> dict:
    """
    Queries nvidia-smi for GPU name, VRAM used, VRAM total, and utilization.
    Returns None gracefully if nvidia-smi is unavailable or no NVIDIA GPU exists.
    """
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                return {
                    "available": True,
                    "name": parts[0],
                    "vram_used_mb": round(float(parts[1])),
                    "vram_total_mb": round(float(parts[2])),
                    "utilization": round(float(parts[3]))
                }
    except Exception:
        pass
    return {"available": False, "name": None, "vram_used_mb": 0, "vram_total_mb": 0, "utilization": 0}

def get_cpu_info() -> dict:
    """Returns CPU usage percentage."""
    try:
        usage = psutil.cpu_percent(interval=None)
        return {"usage": round(usage, 1)}
    except Exception:
        return {"usage": 0}

def get_ram_info() -> dict:
    """Returns system RAM usage in MB and percentage."""
    try:
        mem = psutil.virtual_memory()
        return {
            "used_mb": round(mem.used / (1024 * 1024)),
            "total_mb": round(mem.total / (1024 * 1024)),
            "percent": round(mem.percent, 1)
        }
    except Exception:
        return {"used_mb": 0, "total_mb": 0, "percent": 0}

def get_ollama_status_info() -> dict:
    """
    Queries local Ollama API /api/ps to retrieve running model information.
    """
    try:
        res = requests.get(OLLAMA_PS_URL, timeout=3)
        if res.status_code == 200:
            data = res.json()
            raw_models = data.get("models", [])
            loaded_models = []
            for m in raw_models:
                model_name = m.get("name", m.get("model", "unknown"))
                size_bytes = m.get("size", 0)
                size_gb = f"{round(size_bytes / (1024**3), 1)} GB" if size_bytes else "Unknown"
                
                # Determine processor offload details
                size_vram = m.get("size_vram", 0)
                if size_bytes and size_vram:
                    gpu_ratio = min(100, round((size_vram / size_bytes) * 100))
                    cpu_ratio = 100 - gpu_ratio
                    processor = f"{cpu_ratio}%/{gpu_ratio}% CPU/GPU" if cpu_ratio > 0 else "100% GPU"
                else:
                    processor = "100% GPU" if size_vram > 0 else "CPU / GPU"

                loaded_models.append({
                    "name": model_name,
                    "size": size_gb,
                    "processor": processor
                })

            return {
                "status": "running",
                "loaded_models": loaded_models,
                "count": len(loaded_models)
            }
    except Exception:
        pass
    return {"status": "offline", "loaded_models": [], "count": 0}

def get_system_status() -> dict:
    """
    Aggregates live real-time metrics for GPU, CPU, RAM, and Ollama.
    Never crashes if a metric source is unavailable.
    """
    gpu = get_gpu_info()
    cpu = get_cpu_info()
    ram = get_ram_info()
    ollama = get_ollama_status_info()

    # Determine active model name from Ollama loaded models list
    active_model_name = None
    if ollama["status"] == "running" and len(ollama["loaded_models"]) > 0:
        active_model_name = ollama["loaded_models"][0]["name"]

    return {
        "gpu": gpu,
        "cpu": cpu,
        "ram": ram,
        "ollama": ollama,
        "active_model": active_model_name,
        "inference_mode": "LOCAL INFERENCE",
        "timestamp": psutil.time.time() if hasattr(psutil, "time") else 0
    }

def get_detailed_models_status() -> dict:
    """
    Retrieves live loaded models breakdown from Ollama /api/ps and system RAM/VRAM resources.
    Conforms to GET /api/models/status API specification.
    """
    from services.router_service import (
        RAM_SAFETY_RESERVE_MB,
        VRAM_SAFETY_RESERVE_MB,
        is_router_model,
        is_model_protected,
        get_multi_model_mode
    )

    multi_mode = get_multi_model_mode()
    is_router_loaded = False

    # 1. Fetch raw loaded models from Ollama /api/ps
    loaded_models_res = []
    try:
        res = requests.get(OLLAMA_PS_URL, timeout=3)
        if res.status_code == 200:
            data = res.json()
            raw_models = data.get("models", [])
            
            for idx, m in enumerate(raw_models):
                model_name = m.get("name", m.get("model", "unknown"))
                size_bytes = m.get("size", 0)
                size_vram_bytes = m.get("size_vram", 0)

                ram_mb = max(0.0, round((size_bytes - size_vram_bytes) / (1024 * 1024), 1))
                vram_mb = round(size_vram_bytes / (1024 * 1024), 1)

                name_lower = model_name.lower()
                is_router = is_router_model(model_name)
                if is_router:
                    is_router_loaded = True

                protected = is_model_protected(model_name)

                if is_router:
                    role = "ROUTER"
                    role_display = "Query Router"
                elif "coder" in name_lower:
                    role = "CODING"
                    role_display = "Coding Model"
                elif "phi" in name_lower:
                    role = "GENERAL QA"
                    role_display = "General QA"
                else:
                    role = "MAIN"
                    role_display = "Main Model"

                if protected:
                    status_str = "PROTECTED"
                else:
                    status_str = "ACTIVE" if idx == 0 else "LOADED"

                loaded_models_res.append({
                    "name": model_name,
                    "role": role,
                    "role_display": role_display,
                    "status": status_str,
                    "protected": protected,
                    "ram_usage_mb": ram_mb,
                    "vram_usage_mb": vram_mb,
                    "size_gb": round(size_bytes / (1024**3), 2)
                })
    except Exception:
        pass

    # 2. Fetch System Memory metrics
    mem = psutil.virtual_memory()
    ram_total_mb = round(mem.total / (1024 * 1024), 1)
    ram_used_mb = round(mem.used / (1024 * 1024), 1)
    ram_available_mb = round(mem.available / (1024 * 1024), 1)

    gpu_info = get_gpu_info()
    if gpu_info.get("available", False):
        vram_total_mb = float(gpu_info.get("vram_total_mb", 0))
        vram_used_mb = float(gpu_info.get("vram_used_mb", 0))
        vram_available_mb = max(0.0, vram_total_mb - vram_used_mb)
    else:
        vram_total_mb = 0.0
        vram_used_mb = 0.0
        vram_available_mb = 0.0

    return {
        "multi_model_mode": multi_mode,
        "router": {
            "name": "qwen2.5:1.5b",
            "role": "Query Router",
            "loaded": is_router_loaded,
            "protected": multi_mode
        },
        "models": loaded_models_res,
        "system": {
            "ram_total_mb": ram_total_mb,
            "ram_used_mb": ram_used_mb,
            "ram_available_mb": ram_available_mb,
            "ram_reserve_mb": RAM_SAFETY_RESERVE_MB,
            "vram_total_mb": vram_total_mb,
            "vram_used_mb": vram_used_mb,
            "vram_available_mb": vram_available_mb,
            "vram_reserve_mb": VRAM_SAFETY_RESERVE_MB
        }
    }

