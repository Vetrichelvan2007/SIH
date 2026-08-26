import json
from pathlib import Path
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# File path for local conversation storage
CONVERSATION_FILE = Path(__file__).parent / "conversation.json"

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

# Initialize FastAPI App
app = FastAPI(
    title="Sovereign AI Workbench Backend",
    description="Local FastAPI backend connecting React frontend to Ollama Qwen2.5-Coder model with JSON persistence",
    version="1.1.0"
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
    query: str = Field(..., description="The input prompt or query from the user")
    task: str = Field(..., description="The target AI task category (e.g., 'coding')")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The generated response text from the model")
    model: str = Field(..., description="The model name used for generation")

# Ollama Configuration
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder"

@app.get("/health")
def health_check():
    """Health check endpoint to verify backend status."""
    return {"status": "ok"}

@app.post("/new-chat")
def new_chat_endpoint():
    """Resets the conversation history by clearing conversation.json."""
    save_conversation([])
    return {"status": "cleared", "message": "Conversation history successfully reset."}

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Receives user query & task, loads conversation context from conversation.json,
    sends full context to Ollama /api/chat, saves assistant response to conversation.json,
    and returns model response.
    """
    # 1. Validate task: only 'coding' supported for now
    if request.task.lower() != "coding":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task '{request.task}' is not supported yet. Currently, only the 'coding' task is supported."
        )

    # 2. Read conversation history from conversation.json
    history = load_conversation()

    # 3. Add user message to history
    user_message = {"role": "user", "content": request.query}
    history.append(user_message)

    # 4. Prepare payload for Ollama /api/chat
    payload = {
        "model": DEFAULT_MODEL,
        "messages": history,
        "stream": False
    }

    # 5. Send request to Ollama /api/chat
    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        data = response.json()
        assistant_content = data.get("message", {}).get("content", "")

        # 6. Add assistant response to history
        assistant_message = {"role": "assistant", "content": assistant_content}
        history.append(assistant_message)

        # 7. Save updated conversation back to conversation.json
        save_conversation(history)

        # 8. Return response to frontend
        return ChatResponse(
            response=assistant_content,
            model=DEFAULT_MODEL
        )

    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error: Could not connect to the local Ollama server at http://localhost:11434. Please make sure the Ollama server is running."
        )
    except Timeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Error: Request to local Ollama server timed out."
        )
    except HTTPError as http_err:
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Error: Model '{DEFAULT_MODEL}' not found in Ollama. Please run 'ollama pull {DEFAULT_MODEL}' in your terminal."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama server returned an HTTP error: {http_err}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error while communicating with Ollama: {str(exc)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
