import json
import time
import uuid
from pathlib import Path
from typing import Optional, List
import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from models.qwen_coder import stream_code_response
from models.phi_answer import stream_answer_response
from services.system_monitor import get_system_status, get_detailed_models_status
from services.model_manager import switch_model_stream
import services.chat_db as chat_db
from services.router_service import (
    get_multi_model_mode,
    set_multi_model_mode,
    update_safety_reserves,
    check_resource_safety,
    classify_query,
    ensure_router_loaded,
    ensure_specialist_loaded,
    ROUTE_MODEL_MAP,
    ROUTE_PRIORITY,
    VALID_ROUTES
)

# Initialize SQLite Chat Database
chat_db.init_db()

# File path for local conversation storage
CONVERSATION_FILE = Path(__file__).parent / "conversation.json"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

# Helper functions for conversation history persistence
def load_conversation() -> list:
    """Reads conversation history from conversation.json. Resets to [] if missing or corrupt."""
    if not CONVERSATION_FILE.exists():
        save_conversation([])
        return []
    try:
        with open(CONVERSATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            save_conversation([])
            return []
    except (json.JSONDecodeError, OSError):
        save_conversation([])
        return []

def save_conversation(history: list) -> None:
    """Writes the conversation history list to conversation.json."""
    try:
        with open(CONVERSATION_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write to conversation.json: {str(e)}"
        )

def check_ollama_models_availability() -> List[dict]:
    """
    Checks local Ollama tags API (http://localhost:11434/api/tags)
    and returns model availability info for qwen2.5-coder and phi4-mini.
    """
    installed_names = set()
    ollama_online = False

    try:
        res = requests.get(OLLAMA_TAGS_URL, timeout=5)
        if res.status_code == 200:
            ollama_online = True
            tags_data = res.json()
            models_list = tags_data.get("models", [])
            for m in models_list:
                name = m.get("name", "").lower()
                installed_names.add(name)
                if ":" in name:
                    installed_names.add(name.split(":")[0])
    except Exception:
        ollama_online = False

    target_models = [
        {
            "id": "qwen2.5-coder",
            "name": "Qwen2.5-Coder",
            "type": "Coding",
            "task": "coding",
            "description": "State-of-the-art coding, code generation, refactoring, and debugging."
        },
        {
            "id": "phi4-mini",
            "name": "Phi-4 Mini",
            "type": "Question / General",
            "task": "question",
            "description": "Optimized for fast reasoning, Q&A, and general on-premise AI synthesis."
        }
    ]

    result = []
    for model_info in target_models:
        model_id = model_info["id"]
        is_installed = ollama_online and (
            model_id.lower() in installed_names or
            f"{model_id.lower()}:latest" in installed_names
        )

        if not ollama_online:
            status_text = "Ollama Offline"
        elif is_installed:
            status_text = "Available"
        else:
            status_text = "Not Installed"

        result.append({
            "id": model_id,
            "name": model_info["name"],
            "type": model_info["type"],
            "task": model_info["task"],
            "available": is_installed,
            "status": status_text,
            "description": model_info["description"]
        })

    return result

# Initialize FastAPI App
app = FastAPI(
    title="Sovereign AI Workbench Controller",
    description="Central controller for routing tasks, monitoring telemetry, and managing model lifecycles",
    version="4.0.0"
)

# Enable CORS for React Frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class ChatRequest(BaseModel):
    message: Optional[str] = Field(None, description="The input prompt or message from user")
    query: Optional[str] = Field(None, description="Backward compatible alias for user prompt")
    task: str = Field("coding", description="Target task: 'coding' or 'question'/'general'")
    multi_model_mode: Optional[bool] = Field(None, description="Optional override for Multi-Model Mode")
    chat_id: Optional[str] = Field(None, description="Target chat session ID")

class CreateChatRequest(BaseModel):
    chat_id: Optional[str] = Field(None, description="Optional unique chat ID")
    title: Optional[str] = Field(None, description="Optional initial chat title")

class RenameChatRequest(BaseModel):
    title: str = Field(..., description="New title for the chat session")

class AddMessageRequest(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content text")
    model_used: Optional[str] = None
    route: Optional[str] = None
    response_time: Optional[float] = None

class ModelSwitchRequest(BaseModel):
    model: str = Field(..., description="Target model ID to switch and verify (e.g., 'qwen2.5-coder' or 'phi4-mini')")

class MultiModelToggleRequest(BaseModel):
    enabled: bool = Field(..., description="Enable (True) or Disable (False) Multi-Model Mode")

class MultiModelConfigRequest(BaseModel):
    ram_safety_reserve_mb: Optional[float] = Field(None, description="RAM safety reserve threshold in MB (default 1024 MB = 1 GB)")
    vram_safety_reserve_mb: Optional[float] = Field(None, description="VRAM safety reserve threshold in MB (default 500 MB)")

def sse_format(event_data: dict) -> str:
    return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

# ==================================================
# CHAT HISTORY REST APIS (SQLITE PERSISTENCE)
# ==================================================

@app.get("/api/chats")
def get_chats_endpoint():
    """Returns list of all saved chats ordered by updated_at descending."""
    return {"chats": chat_db.get_all_chats()}

@app.post("/api/chats")
def create_chat_endpoint(req: CreateChatRequest):
    """Creates a new empty chat session."""
    chat = chat_db.create_chat(chat_id=req.chat_id, title=req.title)
    return {"status": "created", "chat": chat}

@app.get("/api/chats/{chat_id}")
def get_chat_endpoint(chat_id: str):
    """Fetches complete chat session by ID including all messages."""
    chat = chat_db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' not found.")
    return chat

@app.delete("/api/chats/{chat_id}")
def delete_chat_endpoint(chat_id: str):
    """Deletes a chat session by ID."""
    deleted = chat_db.delete_chat(chat_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' not found.")
    return {"status": "deleted", "chat_id": chat_id}

@app.patch("/api/chats/{chat_id}")
def rename_chat_endpoint(chat_id: str, req: RenameChatRequest):
    """Renames an existing chat session."""
    chat = chat_db.update_chat_title(chat_id, req.title)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' not found.")
    return {"status": "renamed", "chat": chat}

@app.post("/api/chats/{chat_id}/messages")
def add_message_endpoint(chat_id: str, req: AddMessageRequest):
    """Appends a message to the specified chat session."""
    msg = chat_db.add_message(
        chat_id=chat_id,
        role=req.role,
        content=req.content,
        model_used=req.model_used,
        route=req.route,
        response_time=req.response_time
    )
    return {"status": "saved", "message": msg}

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/models")
def get_available_models():
    """Endpoint returning local Ollama model availability for qwen2.5-coder and phi4-mini."""
    return {"models": check_ollama_models_availability()}

@app.get("/api/system/status")
def system_status_endpoint():
    """
    Live real-time system metrics endpoint returning GPU VRAM, GPU utilization,
    CPU usage %, system RAM, and running Ollama models.
    """
    return get_system_status()

@app.get("/api/models/status")
def models_status_endpoint():
    """
    Returns live dynamically detected loaded models in RAM/VRAM, model roles,
    statuses (ACTIVE/LOADED/LOADING/UNLOADING/FAILED), and system RAM & VRAM reserves.
    """
    return get_detailed_models_status()

@app.get("/api/multi-model/status")
def multi_model_status_endpoint():
    """
    Returns current status of Multi-Model Mode, router model info, safety reserves, and route mappings.
    """
    return {
        "multi_model_mode": get_multi_model_mode(),
        "router_model": "qwen2.5:1.5b",
        "routes": VALID_ROUTES,
        "priority": ["DOCUMENT", "RAG", "CODING", "REASONING", "GENERAL"],
        "route_mapping": ROUTE_MODEL_MAP
    }

@app.post("/api/multi-model/toggle")
def toggle_multi_model_endpoint(request: MultiModelToggleRequest):
    """
    Toggles Multi-Model Mode ON or OFF.
    When set to OFF: immediately unloads qwen2.5:1.5b router from VRAM and releases RAM/VRAM resources.
    """
    result = set_multi_model_mode(request.enabled)
    return {
        "status": "success",
        "message": f"Multi-Model Mode is now {'ON' if request.enabled else 'OFF'}",
        **result
    }

@app.post("/api/multi-model/config")
def config_multi_model_endpoint(request: MultiModelConfigRequest):
    """
    Updates RAM and VRAM safety reserves.
    """
    result = update_safety_reserves(request.ram_safety_reserve_mb, request.vram_safety_reserve_mb)
    return {
        "status": "updated",
        **result
    }

@app.post("/api/models/switch")
def switch_model_endpoint(request: ModelSwitchRequest):
    """
    Real model transition API:
    1. Inspects currently loaded VRAM models.
    2. If target model is already loaded, returns ready state immediately.
    3. Unloads previous model using keep_alive: 0 and verifies memory release.
    4. Loads new model using keep_alive: '1h' and verifies VRAM allocation.
    Returns live SSE event stream.
    """
    return StreamingResponse(
        switch_model_stream(request.model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/new-chat")
def new_chat_endpoint():
    """Resets the conversation history by clearing conversation.json."""
    save_conversation([])
    return {"status": "cleared", "message": "Conversation history successfully reset."}

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    """
    Streaming chat endpoint emitting real Server-Sent Events (SSE):
    - Single-Model Mode (OFF - DEFAULT): 0 routing overhead, direct execution.
    - Multi-Model Mode (ON - OPTIONAL): Qwen2.5 1.5B intent router, RAM/VRAM safety checks, lazy loading, priority hierarchy.
    - Persistent Chat History: Automatically persists messages and manages context window.
    """
    user_text = request.message or request.query
    if not user_text or not user_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request message cannot be empty."
        )

    use_multi_model = request.multi_model_mode if request.multi_model_mode is not None else get_multi_model_mode()
    req_task = (request.task or "coding").lower().strip()
    target_chat_id = request.chat_id or str(uuid.uuid4())

    # Save user message to persistent SQLite database
    chat_db.add_message(chat_id=target_chat_id, role="user", content=user_text)

    def generate_events():
        # Initialize task_clean at the top of generate_events scope to guarantee it exists in all paths
        task_clean = "coding" if req_task in ["coding", "code"] else "general"
        selected_route = "CODING" if task_clean == "coding" else "GENERAL"
        start_time = time.perf_counter()

        try:
            # 1. Query received
            yield sse_format({"type": "status", "stage": "query_received", "message": "Query received", "chat_id": target_chat_id})

            # 2. Sent to backend / processing
            backend_start = time.perf_counter()
            yield sse_format({"type": "status", "stage": "backend_processing", "message": "Request sent to FastAPI backend", "chat_id": target_chat_id})

            if not use_multi_model:
                # ==================================================
                # 1. SINGLE-MODEL MODE (OFF - DEFAULT)
                # ZERO ROUTING OVERHEAD, DIRECT MODEL PIPELINE
                # ==================================================
                is_coding = task_clean == "coding"
                task_label = "Coding" if is_coding else "Question / General"
                model_id = "qwen2.5-coder" if is_coding else "phi4-mini"
                model_name = "Qwen2.5-Coder" if is_coding else "Phi-4 Mini"

                yield sse_format({"type": "status", "stage": "task_selected", "message": f"Task identified: {task_label}", "task": task_clean, "task_label": task_label, "multi_model": False, "chat_id": target_chat_id})
                yield sse_format({"type": "status", "stage": "model_selected", "message": f"Model selected: {model_name}", "model": model_id, "model_name": model_name, "chat_id": target_chat_id})
            else:
                # ==================================================
                # 2. MULTI-MODEL MODE (ON - OPTIONAL)
                # ROUTER: Qwen2.5 1.5B with Memory Management & Safety Verification
                # ==================================================
                yield sse_format({"type": "status", "stage": "multi_model_routing", "message": "Multi-Model Mode Active: Preparing Qwen2.5 1.5B Router...", "multi_model": True, "chat_id": target_chat_id})

                # Step 1 & 2: Ensure Router is loaded (unloads current inference model if memory is insufficient)
                router_loaded, router_msg = ensure_router_loaded()
                
                router_safe, _, router_metrics = check_resource_safety("qwen2.5:1.5b")
                yield sse_format({
                    "type": "status",
                    "stage": "resource_safety_check",
                    "target": "Router (qwen2.5:1.5b)",
                    "is_safe": router_safe,
                    "message": router_msg,
                    "metrics": router_metrics,
                    "chat_id": target_chat_id
                })

                # Step 3: Classify query via Router (Qwen2.5 1.5B with fallback)
                try:
                    raw_route, router_info = classify_query(user_text)
                    selected_route = str(raw_route or "GENERAL").strip().upper()
                    if selected_route not in VALID_ROUTES:
                        selected_route = "GENERAL"
                except Exception as r_err:
                    print(f"Router error: {r_err}")
                    selected_route = "GENERAL"
                    router_info = {"method": "router_error_fallback", "message": str(r_err), "route": "GENERAL"}

                # Explicit Route-to-Model Mapping
                if selected_route == "CODING":
                    target_model_id = "qwen2.5-coder"
                    target_model_name = "Qwen2.5-Coder"
                    task_clean = "coding"
                elif selected_route == "GENERAL":
                    target_model_id = "phi4-mini"
                    target_model_name = "Phi-4 Mini"
                    task_clean = "general"
                elif selected_route == "REASONING":
                    target_model_id = "phi4-mini"
                    target_model_name = "Phi-4 Mini"
                    task_clean = "reasoning"
                elif selected_route == "RAG":
                    target_model_id = "phi4-mini"
                    target_model_name = "Phi-4 Mini"
                    task_clean = "rag"
                elif selected_route == "DOCUMENT":
                    target_model_id = "phi4-mini"
                    target_model_name = "Phi-4 Mini"
                    task_clean = "document"
                else:
                    selected_route = "GENERAL"
                    target_model_id = "phi4-mini"
                    target_model_name = "Phi-4 Mini"
                    task_clean = "general"

                # Backend Debug Logging
                raw_out_str = router_info.get("raw_output", selected_route)
                print("\n" + "="*50)
                print("[ROUTER]")
                print(f"Query: {user_text}")
                print(f"Raw output: {raw_out_str}")
                print(f"Normalized route: {selected_route}")
                print(f"Selected model: {target_model_name}")
                print("="*50 + "\n")

                yield sse_format({
                    "type": "status",
                    "stage": "route_classified",
                    "route": selected_route,
                    "priority": "DOCUMENT > RAG > CODING > REASONING > GENERAL",
                    "message": f"Route classified: {selected_route}",
                    "router_info": router_info,
                    "chat_id": target_chat_id
                })

                task_label = f"Multi-Model Route [{selected_route}]"

                # Step 4 & 5: Ensure Specialist Model is loaded (unloads Router model if memory safety requires it)
                spec_loaded, spec_msg = ensure_specialist_loaded(target_model_id)

                if not spec_loaded:
                    # Safe Fallback to default active model
                    yield sse_format({
                        "type": "status",
                        "stage": "resource_fallback",
                        "message": f"⚠️ Safety limit reached for {target_model_name}: {spec_msg}. Falling back safely to default active model.",
                        "chat_id": target_chat_id
                    })
                    model_id = "phi4-mini"
                    model_name = "Phi-4 Mini"
                else:
                    model_id = target_model_id
                    model_name = target_model_name

                yield sse_format({"type": "status", "stage": "task_selected", "message": f"Task identified: {task_label}", "task": task_clean, "task_label": task_label, "route": selected_route, "multi_model": True, "chat_id": target_chat_id})
                yield sse_format({"type": "status", "stage": "model_selected", "message": f"Model selected: {model_name}", "model": model_id, "model_name": model_name, "chat_id": target_chat_id})

            # Safe Route Checks
            is_coding = task_clean == "coding"
            is_reasoning = task_clean == "reasoning"
            is_rag = task_clean == "rag"
            is_document = task_clean == "document"
            is_general = task_clean == "general"

            # Context Window Trimming: Retrieve last N messages for model prompt from persistent SQLite chat DB
            model_messages = chat_db.get_trimmed_model_messages(target_chat_id, max_messages=15)
            
            # Legacy file backup
            legacy_history = load_conversation()
            legacy_history.append({"role": "user", "content": user_text})
            
            backend_overhead_time = round(time.perf_counter() - backend_start, 3)

            # Connected to local Ollama API
            yield sse_format({"type": "status", "stage": "ollama_connecting", "message": "Connecting to local Ollama API", "chat_id": target_chat_id})

            # Model processing locally
            yield sse_format({"type": "status", "stage": "ollama_processing", "message": f"{model_name} is processing locally...", "chat_id": target_chat_id})

            model_start = time.perf_counter()
            accumulated_tokens = []

            if is_coding:
                stream = stream_code_response(model_messages)
            else:
                stream = stream_answer_response(model_messages)

            first_chunk = True
            for token in stream:
                if first_chunk:
                    yield sse_format({"type": "status", "stage": "receiving_response", "message": "Receiving model response...", "chat_id": target_chat_id})
                    first_chunk = False

                accumulated_tokens.append(token)
                yield sse_format({"type": "token", "content": token})

            model_gen_time = round(time.perf_counter() - model_start, 2)
            total_time = round(time.perf_counter() - start_time, 2)

            full_response = "".join(accumulated_tokens)

            # Update legacy conversation.json
            legacy_history.append({"role": "assistant", "content": full_response})
            save_conversation(legacy_history)

            # Save assistant response to persistent SQLite DB
            chat_db.add_message(
                chat_id=target_chat_id,
                role="assistant",
                content=full_response,
                model_used=model_name,
                route=selected_route,
                response_time=total_time
            )

            # Completed event with timing metrics
            yield sse_format({"type": "status", "stage": "completed", "message": "Response completed", "chat_id": target_chat_id})

            yield sse_format({
                "type": "complete",
                "chat_id": target_chat_id,
                "model": model_id,
                "model_name": model_name,
                "multi_model_mode": use_multi_model,
                "metrics": {
                    "total_response_time": total_time,
                    "backend_time": backend_overhead_time,
                    "model_time": model_gen_time
                }
            })

        except HTTPException as http_exc:
            print(f"HTTPException in generate_events: {http_exc.detail}")
            yield sse_format({"type": "error", "stage": "error", "message": http_exc.detail})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            yield sse_format({"type": "error", "stage": "error", "message": f"Server processing error: {str(exc)}"})

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
