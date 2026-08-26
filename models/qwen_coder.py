import json
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError
from fastapi import HTTPException, status

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODEL_ID = "qwen2.5-coder"

def generate_code_response(messages: list) -> str:
    """Non-streaming code generation fallback."""
    tokens = list(stream_code_response(messages))
    return "".join(tokens)

def stream_code_response(messages: list):
    """
    Communicates with local Ollama instance using Qwen2.5-Coder with stream=True.
    Yields individual token strings as they arrive from Ollama.
    """
    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "stream": True
    }

    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json=payload,
            stream=True,
            timeout=180
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode('utf-8'))
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue

    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error: Could not connect to local Ollama server at http://localhost:11434. Please ensure Ollama is running."
        )
    except Timeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Error: Request to local Ollama model '{MODEL_ID}' timed out."
        )
    except HTTPError as http_err:
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Error: Model '{MODEL_ID}' not found in local Ollama instance. Please run 'ollama pull {MODEL_ID}' in your terminal."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama server returned an HTTP error for '{MODEL_ID}': {http_err}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error while communicating with Ollama model '{MODEL_ID}': {str(exc)}"
        )
