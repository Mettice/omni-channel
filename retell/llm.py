"""
LLM operations for Omni AI using OpenAI.
"""
import json
import httpx
from typing import Optional

try:
    from .config import (
        OPENAI_API_KEY,
        OPENAI_TIMEOUT,
        MAX_TOKENS,
        logger
    )
except ImportError:
    from config import (
        OPENAI_API_KEY,
        OPENAI_TIMEOUT,
        MAX_TOKENS,
        logger
    )

# Shared HTTP client for connection pooling
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create shared async HTTP client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=OPENAI_TIMEOUT)
    return _http_client


async def close_http_client():
    """Close the shared HTTP client (call on shutdown)."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


async def generate_response(messages: list) -> str:
    """
    Non-streaming response generation for chat endpoint.

    Args:
        messages: List of OpenAI-format messages

    Returns:
        Generated response text

    Raises:
        RuntimeError: If API key not set or API call fails
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = await get_http_client()

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": MAX_TOKENS
    }

    try:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=OPENAI_TIMEOUT
        )
    except httpx.TimeoutException:
        raise RuntimeError("OpenAI API request timed out")
    except httpx.RequestError as e:
        raise RuntimeError(f"OpenAI API request failed: {e}")

    try:
        data = res.json()
    except Exception:
        raise RuntimeError(f"OpenAI returned non-JSON response (HTTP {res.status_code})")

    if res.status_code >= 400:
        err = data.get("error") if isinstance(data, dict) else None
        msg = err.get("message") if isinstance(err, dict) else str(data)
        raise RuntimeError(f"OpenAI API error (HTTP {res.status_code}): {msg}")

    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices:
        raise RuntimeError(f"OpenAI response missing choices: {data}")

    return choices[0]["message"]["content"]


async def generate_response_streaming(messages: list, ws, response_id: int) -> str:
    """
    Streaming response generation for Retell Custom LLM.
    Streams tokens directly to the WebSocket and returns the full response.

    Args:
        messages: List of OpenAI-format messages
        ws: WebSocket connection to stream to
        response_id: Retell response ID for correlation

    Returns:
        Full generated response text

    Raises:
        RuntimeError: If API key not set or API call fails
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "stream": True
    }

    full_response = ""

    # Use a fresh client for streaming to avoid connection issues
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=OPENAI_TIMEOUT
            ) as res:
                if res.status_code >= 400:
                    error_body = await res.aread()
                    raise RuntimeError(f"OpenAI API error (HTTP {res.status_code}): {error_body.decode()}")

                async for line in res.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            full_response += content
                            # Stream this chunk to Retell
                            await ws.send_str(json.dumps({
                                "response_id": response_id,
                                "content": content,
                                "content_complete": False
                            }))
                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException:
            raise RuntimeError("OpenAI streaming request timed out")
        except httpx.RequestError as e:
            raise RuntimeError(f"OpenAI streaming request failed: {e}")

    # Send completion signal to Retell
    await ws.send_str(json.dumps({
        "response_id": response_id,
        "content": "",
        "content_complete": True
    }))

    return full_response
