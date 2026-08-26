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
