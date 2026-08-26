import json
import time
from pathlib import Path
from typing import Optional, List
import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from models.qwen_coder import stream_code_response
from models.phi_answer import stream_answer_response
from services.system_monitor import get_system_status
from services.model_manager import switch_model_stream

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
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class ChatRequest(BaseModel):
    message: Optional[str] = Field(None, description="The input prompt or message from user")
    query: Optional[str] = Field(None, description="Backward compatible alias for user prompt")
    task: str = Field("coding", description="Target task: 'coding' or 'question'/'general'")

class ModelSwitchRequest(BaseModel):
    model: str = Field(..., description="Target model ID to switch and verify (e.g., 'qwen2.5-coder' or 'phi4-mini')")

def sse_format(event_data: dict) -> str:
    return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

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
    - Status events: query_received, backend_processing, task_selected, model_selected, ollama_connecting, ollama_processing, receiving_response, completed
    - Token events: streamed token contents
    - Metrics event: total response time, backend time, model processing time
    - Error events: connection/model error details
    """
    user_text = request.message or request.query
    if not user_text or not user_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request message cannot be empty."
        )

    task_clean = request.task.lower().strip()

    def generate_events():
        start_time = time.perf_counter()

        # 1. Query received
        yield sse_format({"type": "status", "stage": "query_received", "message": "Query received"})

        # 2. Sent to backend / processing
        backend_start = time.perf_counter()
        yield sse_format({"type": "status", "stage": "backend_processing", "message": "Request sent to FastAPI backend"})

        is_coding = task_clean in ["coding", "code"]
        task_label = "Coding" if is_coding else "Question / General"
        model_id = "qwen2.5-coder" if is_coding else "phi4-mini"
        model_name = "Qwen2.5-Coder" if is_coding else "Phi-4 Mini"

        # 3. Task identified
        yield sse_format({"type": "status", "stage": "task_selected", "message": f"Task identified: {task_label}", "task": task_clean, "task_label": task_label})

        # 4. Model selected
        yield sse_format({"type": "status", "stage": "model_selected", "message": f"Model selected: {model_name}", "model": model_id, "model_name": model_name})

        # Load conversation history
        history = load_conversation()
        user_msg = {"role": "user", "content": user_text}
        history.append(user_msg)
        backend_overhead_time = round(time.perf_counter() - backend_start, 3)

        # 5. Connected to local Ollama
        yield sse_format({"type": "status", "stage": "ollama_connecting", "message": "Connecting to local Ollama API"})

        # 6. Model processing locally
        yield sse_format({"type": "status", "stage": "ollama_processing", "message": f"{model_name} is processing locally..."})

        model_start = time.perf_counter()
        accumulated_tokens = []

        try:
            if is_coding:
                stream = stream_code_response(history)
            elif task_clean in ["question", "general", "answer", "qa"]:
                stream = stream_answer_response(history)
            else:
                yield sse_format({"type": "error", "stage": "error", "message": f"Invalid task '{request.task}'."})
                return

            first_chunk = True
            for token in stream:
                if first_chunk:
                    yield sse_format({"type": "status", "stage": "receiving_response", "message": "Receiving model response..."})
                    first_chunk = False

                accumulated_tokens.append(token)
                yield sse_format({"type": "token", "content": token})

            model_gen_time = round(time.perf_counter() - model_start, 2)
            total_time = round(time.perf_counter() - start_time, 2)

            full_response = "".join(accumulated_tokens)

            # Update conversation history
            assistant_msg = {"role": "assistant", "content": full_response}
            history.append(assistant_msg)
            save_conversation(history)

            # 7. Completed event with timing metrics
            yield sse_format({"type": "status", "stage": "completed", "message": "Response completed"})

            yield sse_format({
                "type": "complete",
                "model": model_id,
                "model_name": model_name,
                "metrics": {
                    "total_response_time": total_time,
                    "backend_time": backend_overhead_time,
                    "model_time": model_gen_time
                }
            })

        except HTTPException as http_exc:
            yield sse_format({"type": "error", "stage": "error", "message": http_exc.detail})
        except Exception as exc:
            yield sse_format({"type": "error", "stage": "error", "message": f"Ollama connection error: {str(exc)}"})

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
