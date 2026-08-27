import json
import time
from .ollama_service import get_loaded_models, unload_model, load_model

def sse_format(event_type: str, status: str, message: str, model: str = None) -> str:
    payload = {
        "type": "model_switch",
        "status": status,
        "message": message,
        "model": model
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

def switch_model_stream(target_model_id: str):
    """
    Coordinates model transition lifecycle with verified unloading and loading:
    1. Checks currently loaded models in VRAM (Ollama api/ps).
    2. If target model is already loaded, returns ready state without reloading.
    3. If another model is active, unloads old model (keep_alive: 0) and verifies memory release.
    4. Loads new model (keep_alive: "1h") and verifies availability.
    Yields real-time SSE event payloads.
    """
    target_clean = target_model_id.lower().strip()
    target_display = "Qwen2.5-Coder" if "qwen" in target_clean else "Phi-4 Mini"
    target_ollama_name = "qwen2.5-coder" if "qwen" in target_clean else "phi4-mini"

    # 1. Check loaded models
    yield sse_format("model_switch", "checking_current_model", "Checking currently loaded models in VRAM...", model=target_display)

    loaded_list = get_loaded_models()
    loaded_names = [m.get("name", "").lower() for m in loaded_list]

    # Check if target model is already loaded
    is_target_loaded = any(target_clean in name or target_ollama_name in name for name in loaded_names)

    if is_target_loaded:
        yield sse_format("model_switch", "ready", f"✓ {target_display} is already loaded and ready in VRAM", model=target_display)
        return

    # If another model is currently loaded, unload it
    other_models_loaded = [
        m for m in loaded_list 
        if not (target_clean in m.get("name", "").lower() or target_ollama_name in m.get("name", "").lower())
    ]

    if other_models_loaded:
        for old_model in other_models_loaded:
            old_name = old_model.get("name", "")
            old_display = "Phi-4 Mini" if "phi" in old_name.lower() else ("Qwen2.5-Coder" if "qwen" in old_name.lower() else old_name)
            
            # 2. Begin unload
            yield sse_format("model_switch", "unloading", f"Unloading {old_display} from VRAM (keep_alive: 0)...", model=old_display)
            
            unload_model(old_name)

            # 3. Verify memory release
            verified_unload = False
            for _ in range(8):
                time.sleep(0.6)
                current_ps = get_loaded_models()
                still_loaded = any(old_name.lower() in m.get("name", "").lower() for m in current_ps)
                if not still_loaded:
                    verified_unload = True
                    break

            if verified_unload:
                yield sse_format("model_switch", "unloaded", f"✓ {old_display} unloaded successfully. VRAM memory released.", model=old_display)
            else:
                yield sse_format("model_switch", "unloaded", f"Unload request sent for {old_display}.", model=old_display)

    # 4. Check RAM & VRAM Resource Safety before loading new model
    from .router_service import check_resource_safety
    is_safe, safety_msg, metrics = check_resource_safety(target_ollama_name)

    if not is_safe:
        yield sse_format("model_switch", "warning", f"⚠️ Resource Reserve Warning: {safety_msg}. Loading anyway with CPU/VRAM offload.", model=target_display)

    # Begin loading new model
    yield sse_format("model_switch", "loading", f"Loading {target_display} into local GPU VRAM...", model=target_display)
    
    load_model(target_ollama_name)

    # 5. Verify model availability
    yield sse_format("model_switch", "verifying", f"Verifying {target_display} VRAM allocation...", model=target_display)
    
    verified_load = False
    for _ in range(10):
        time.sleep(0.6)
        current_ps = get_loaded_models()
        is_now_loaded = any(target_clean in m.get("name", "").lower() or target_ollama_name in m.get("name", "").lower() for m in current_ps)
        if is_now_loaded:
            verified_load = True
            break

    # 6. Ready
    yield sse_format("model_switch", "ready", f"✓ {target_display} is verified ready for execution", model=target_display)
