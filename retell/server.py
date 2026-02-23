"""
Omni AI - Multi-Channel Customer Support Server

Main entry point for the aiohttp server with HTTP and WebSocket endpoints.
"""
import json
import asyncio
import re
import time
from collections import defaultdict
from aiohttp import web
import aiohttp

from .config import (
    RETELL_AGENT_ID,
    RETELL_API_KEY,
    STREAMING_CHUNK_DELAY,
    N8N_WEBHOOK_BASE,
    VOICE_AGENTS,
    get_voice_agent,
    get_system_prompt,
    get_greeting,
    logger
)
from .db import (
    get_customer_messages,
    save_message,
    store_call_mapping,
    get_call_mapping,
    delete_call_mapping
)
from .llm import (
    generate_response,
    generate_response_streaming,
    close_http_client
)
from .intents import detect_and_trigger_intents
from .embeddings import detect_intents_hybrid
from .summarization import smart_context_management
from .analytics import (
    start_conversation,
    track_message,
    track_intent,
    end_conversation,
    get_dashboard_stats,
    get_conversations_list
)

# === Rate Limiting ===
# Simple in-memory rate limiter (use Redis in production for multi-instance)
RATE_LIMIT_REQUESTS = 30  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(client_id: str) -> bool:
    """
    Check if client has exceeded rate limit.
    Returns True if request is allowed, False if rate limited.
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries and add new one
    _rate_limit_store[client_id] = [
        t for t in _rate_limit_store[client_id] if t > window_start
    ]

    if len(_rate_limit_store[client_id]) >= RATE_LIMIT_REQUESTS:
        return False

    _rate_limit_store[client_id].append(now)
    return True


# === Input Validation ===
# Pattern for valid customer/player IDs (alphanumeric, underscore, hyphen, 1-100 chars)
VALID_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')
MAX_MESSAGE_LENGTH = 2000


def validate_customer_id(customer_id: str) -> tuple[bool, str]:
    """Validate customer ID format. Returns (is_valid, error_message)."""
    if not customer_id:
        return False, "customer_id is required"
    if not isinstance(customer_id, str):
        return False, "customer_id must be a string"
    if not VALID_ID_PATTERN.match(customer_id):
        return False, "customer_id contains invalid characters"
    return True, ""


def validate_message(message: str) -> tuple[bool, str]:
    """Validate message format. Returns (is_valid, error_message)."""
    if not message:
        return False, "message is required"
    if not isinstance(message, str):
        return False, "message must be a string"
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"message exceeds maximum length of {MAX_MESSAGE_LENGTH}"
    return True, ""


def sanitize_message(message: str) -> str:
    """Sanitize message content."""
    # Remove null bytes and control characters (except newlines)
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', message).strip()


# === CORS Helpers ===
def _corsify(resp: web.StreamResponse) -> web.StreamResponse:
    """Add CORS headers to response."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


def _get_client_ip(request: web.Request) -> str:
    """Extract client IP for rate limiting."""
    # Check for proxy headers first
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote or "unknown"


# === HTTP Handlers ===

async def health(request: web.Request) -> web.Response:
    """Health check endpoint for monitoring."""
    return web.json_response({
        "status": "ok",
        "service": "omni-ai",
        "version": "1.0.0"
    })


# === Analytics API Endpoints ===

async def api_analytics_stats(request: web.Request) -> web.Response:
    """Get dashboard statistics."""
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    days = int(request.query.get("days", 7))
    stats = await get_dashboard_stats(days)
    return _corsify(web.json_response(stats))


async def api_analytics_conversations(request: web.Request) -> web.Response:
    """Get list of conversations."""
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    limit = int(request.query.get("limit", 50))
    offset = int(request.query.get("offset", 0))
    channel = request.query.get("channel")

    conversations = await get_conversations_list(limit, offset, channel)
    return _corsify(web.json_response({"conversations": conversations}))


# === Domain Config API Endpoints ===

async def api_domains_list(request: web.Request) -> web.Response:
    """Get list of all domain configurations."""
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    from .db import get_supabase
    supabase = get_supabase()
    if not supabase:
        return _corsify(web.json_response({"error": "Database not configured"}, status=500))

    try:
        result = supabase.table("domain_configs").select("*").order("domain").execute()
        return _corsify(web.json_response({"domains": result.data or []}))
    except Exception as e:
        logger.error(f"Failed to get domains: {e}")
        return _corsify(web.json_response({"error": str(e)}, status=500))


async def api_domain_update(request: web.Request) -> web.Response:
    """Update a domain configuration."""
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    try:
        payload = await request.json()
    except Exception:
        return _corsify(web.json_response({"error": "Invalid JSON"}, status=400))

    domain = payload.get("domain")
    if not domain:
        return _corsify(web.json_response({"error": "domain is required"}, status=400))

    from .db import get_supabase
    supabase = get_supabase()
    if not supabase:
        return _corsify(web.json_response({"error": "Database not configured"}, status=500))

    try:
        # Update only provided fields
        update_data = {}
        for field in ["display_name", "system_prompt", "greeting", "primary_color", "logo_url", "active"]:
            if field in payload:
                update_data[field] = payload[field]

        if update_data:
            update_data["updated_at"] = "now()"
            supabase.table("domain_configs").update(update_data).eq("domain", domain).execute()

        return _corsify(web.json_response({"success": True}))
    except Exception as e:
        logger.error(f"Failed to update domain: {e}")
        return _corsify(web.json_response({"error": str(e)}, status=500))


async def api_domain_create(request: web.Request) -> web.Response:
    """Create a new domain configuration."""
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    try:
        payload = await request.json()
    except Exception:
        return _corsify(web.json_response({"error": "Invalid JSON"}, status=400))

    required = ["domain", "display_name", "system_prompt", "greeting"]
    for field in required:
        if field not in payload:
            return _corsify(web.json_response({"error": f"{field} is required"}, status=400))

    from .db import get_supabase
    supabase = get_supabase()
    if not supabase:
        return _corsify(web.json_response({"error": "Database not configured"}, status=500))

    try:
        supabase.table("domain_configs").insert({
            "domain": payload["domain"],
            "display_name": payload["display_name"],
            "system_prompt": payload["system_prompt"],
            "greeting": payload["greeting"],
            "primary_color": payload.get("primary_color", "#6366f1"),
            "logo_url": payload.get("logo_url"),
            "active": payload.get("active", True)
        }).execute()

        return _corsify(web.json_response({"success": True}))
    except Exception as e:
        logger.error(f"Failed to create domain: {e}")
        return _corsify(web.json_response({"error": str(e)}, status=500))


# === Voice Selection API ===

async def api_voices_list(request: web.Request) -> web.StreamResponse:
    """List available voice options for the UI."""
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    voices = []
    for voice_id, config in VOICE_AGENTS.items():
        voices.append({
            "id": voice_id,
            "name": config["name"],
            "language": config["language"],
            "gender": config["gender"],
            "description": config["description"],
            "preview_url": config.get("preview_url")
        })

    return _corsify(web.json_response({"voices": voices}))


async def create_call(request: web.Request) -> web.StreamResponse:
    """Create a new Retell voice call with optional voice selection."""
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    # Rate limiting
    client_ip = _get_client_ip(request)
    if not check_rate_limit(f"create_call:{client_ip}"):
        return _corsify(web.json_response(
            {"error": "Rate limit exceeded. Please try again later."},
            status=429
        ))

    if not RETELL_API_KEY:
        return _corsify(web.json_response(
            {"error": "RETELL_API_KEY is not configured"},
            status=500
        ))

    # Get and validate customer_id
    customer_id = request.query.get("customer_id", "unknown")
    is_valid, error = validate_customer_id(customer_id)
    if not is_valid:
        return _corsify(web.json_response({"error": error}, status=400))

    # Get voice selection (optional)
    voice_id = request.query.get("voice_id", "default")
    voice_config = get_voice_agent(voice_id)
    agent_id = voice_config["agent_id"]

    logger.info(f"Creating call for customer: {customer_id} with voice: {voice_config['name']}")

    payload = {
        "agent_id": agent_id,
        "metadata": {"customer_id": customer_id, "voice_id": voice_id}
    }
    headers = {
        "Authorization": f"Bearer {RETELL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.retellai.com/v2/create-web-call",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception:
                    data = {"raw": text}

                if resp.status >= 400:
                    logger.error(f"Retell API error: {data}")
                    # Extract readable error message from Retell response
                    error_msg = data.get("message") or data.get("error") or str(data)
                    return _corsify(web.json_response({"error": error_msg}, status=resp.status))

                access_token = data.get("access_token")
                call_id = data.get("call_id")

                if not access_token:
                    return _corsify(web.json_response(
                        {"error": "Missing access_token", "data": data},
                        status=500
                    ))

                # Store mapping in database for persistence
                if call_id:
                    store_call_mapping(call_id, customer_id)
                    logger.info(f"Mapped call {call_id} -> customer {customer_id}")

                return _corsify(web.json_response({"access_token": access_token}))
    except asyncio.TimeoutError:
        logger.error("Retell API timeout")
        return _corsify(web.json_response({"error": "Request timeout"}, status=504))
    except Exception as e:
        logger.error(f"Create call error: {e}")
        return _corsify(web.json_response({"error": str(e)}, status=500))


async def chat(request: web.Request) -> web.StreamResponse:
    """Handle chat messages."""
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    # Rate limiting
    client_ip = _get_client_ip(request)
    if not check_rate_limit(f"chat:{client_ip}"):
        return _corsify(web.json_response(
            {"error": "Rate limit exceeded. Please try again later."},
            status=429
        ))

    try:
        payload = await request.json()
    except Exception:
        return _corsify(web.json_response({"error": "Invalid JSON body"}, status=400))

    # Validate inputs
    customer_id = payload.get("player_id")  # Keep 'player_id' for API compatibility
    is_valid, error = validate_customer_id(customer_id)
    if not is_valid:
        return _corsify(web.json_response({"error": error}, status=400))

    message = payload.get("message", "")
    is_valid, error = validate_message(message)
    if not is_valid:
        return _corsify(web.json_response({"error": error}, status=400))

    message = sanitize_message(message)
    request_start = time.time()

    # Start tracking conversation
    start_conversation(customer_id, "chat")

    # Persist user message first
    save_message(customer_id, "user", message, channel="web")
    track_message(customer_id, "user", "chat")

    # Get history and apply smart summarization if needed
    history = get_customer_messages(customer_id)
    history = await smart_context_management(history)

    try:
        response = await generate_response(
            [{"role": "system", "content": get_system_prompt()}]
            + history
            + [{"role": "user", "content": message}]
        )
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        return _corsify(web.json_response({"error": str(e)}, status=500))

    # Calculate response time
    response_time_ms = (time.time() - request_start) * 1000

    save_message(customer_id, "agent", response, channel="web")
    track_message(customer_id, "agent", "chat", response_time_ms=response_time_ms)

    # Detect intents using hybrid approach (semantic + keyword)
    asyncio.create_task(_process_intents(customer_id, message, "chat"))

    return _corsify(web.json_response({"response": response}))


async def _process_intents(customer_id: str, message: str, channel: str):
    """Process intents using hybrid detection and trigger webhooks."""
    try:
        # Use semantic detection first, fall back to keywords
        detected_intents = await detect_intents_hybrid(message)

        for intent_name, confidence, webhook_path in detected_intents:
            # Track the intent
            track_intent(customer_id, intent_name, confidence, webhook_triggered=bool(N8N_WEBHOOK_BASE))

            # Trigger n8n webhook if configured
            if N8N_WEBHOOK_BASE:
                await detect_and_trigger_intents(customer_id, message, channel)

    except Exception as e:
        logger.error(f"Intent processing error: {e}")


# === WebSocket Handler ===

async def stream_text_to_retell(ws, text: str, response_id: int):
    """
    Stream pre-generated text to Retell token by token.
    Used for greetings or fallback responses.
    """
    words = text.split(" ")
    for i, word in enumerate(words):
        # Add space before word (except first word)
        chunk = word if i == 0 else " " + word
        await ws.send_str(json.dumps({
            "response_id": response_id,
            "content": chunk,
            "content_complete": False
        }))
        await asyncio.sleep(STREAMING_CHUNK_DELAY)

    # Send completion signal
    await ws.send_str(json.dumps({
        "response_id": response_id,
        "content": "",
        "content_complete": True
    }))


async def llm_websocket(request: web.Request) -> web.StreamResponse:
    """Handle Retell LLM WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    call_id = request.match_info.get("call_id", "unknown")

    # Try to look up customer_id from database
    customer_id = get_call_mapping(call_id)
    logger.info(f"=== NEW CALL ===")
    logger.info(f"Call ID: {call_id}")
    logger.info(f"Initial customer_id from DB: {customer_id}")

    # Track if we've sent initial greeting
    greeting_sent = False
    history = []

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                message_text = msg.data
            elif msg.type == web.WSMsgType.BINARY:
                message_text = msg.data.decode("utf-8", errors="replace")
            elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                break
            else:
                continue

            data = json.loads(message_text)
            interaction_type = data.get("interaction_type")
            response_id = data.get("response_id", 0)
            logger.debug(f"Received event: {interaction_type}")

            if interaction_type == "call_details":
                # Extract customer_id from metadata (survives server restarts)
                call_data = data.get("call", {})
                metadata = call_data.get("metadata", {})
                metadata_customer_id = metadata.get("customer_id")

                if metadata_customer_id:
                    customer_id = metadata_customer_id
                    logger.info(f"Got customer_id from metadata: {customer_id}")
                elif not customer_id:
                    # Fallback to call_id if nothing else works
                    customer_id = call_id
                    logger.info(f"Fallback to call_id as customer_id: {customer_id}")

                # Now load history with the correct customer_id
                history = get_customer_messages(customer_id)
                logger.info(f"Loaded {len(history)} messages from history for {customer_id}")
                continue

            if interaction_type == "ping_pong":
                # Respond to keep-alive pings
                await ws.send_str(json.dumps({
                    "response_type": "ping_pong",
                    "timestamp": data.get("timestamp", 0)
                }))
                continue

            if interaction_type == "update_only":
                # Just a transcript update, no response needed
                continue

            if interaction_type == "response_required":
                # Ensure we have a customer_id
                if not customer_id:
                    customer_id = call_id
                    logger.warning(f"customer_id not set, using call_id: {customer_id}")

                transcript = data.get("transcript", [])
                request_start = time.time()

                # Find the last user message
                last_user_msg = ""
                for t in reversed(transcript):
                    if t.get("role") == "user":
                        last_user_msg = t.get("content", "")
                        break

                # If no user message yet, send greeting
                if not last_user_msg and not greeting_sent:
                    greeting = get_greeting()
                    logger.info(f"Streaming greeting to {customer_id}")
                    await stream_text_to_retell(ws, greeting, response_id)
                    save_message(customer_id, "agent", greeting)
                    start_conversation(customer_id, "voice")
                    track_message(customer_id, "agent", "voice")
                    greeting_sent = True
                    continue

                if last_user_msg:
                    # Sanitize and save user message
                    last_user_msg = sanitize_message(last_user_msg)
                    save_message(customer_id, "user", last_user_msg)
                    track_message(customer_id, "user", "voice")
                    greeting_sent = True  # User spoke, so greeting phase is over

                # Reload history and apply smart summarization
                history = get_customer_messages(customer_id)
                history = await smart_context_management(history)
                logger.debug(f"History loaded for {customer_id}: {len(history)} messages")

                prompt = last_user_msg if last_user_msg else "greet the customer warmly"

                logger.info(f"Generating response for {customer_id}: {prompt[:50]}...")

                try:
                    # Build messages: system + history + current user message
                    messages = [{"role": "system", "content": get_system_prompt()}]
                    messages.extend(history)
                    messages.append({"role": "user", "content": prompt})

                    response = await generate_response_streaming(
                        messages,
                        ws,
                        response_id
                    )

                    # Calculate response time
                    response_time_ms = (time.time() - request_start) * 1000

                    logger.info(f"Streamed response: {response[:100]}...")
                    save_message(customer_id, "agent", response)
                    track_message(customer_id, "agent", "voice", response_time_ms=response_time_ms)

                    # Process intents using hybrid detection
                    asyncio.create_task(_process_intents(customer_id, last_user_msg, "voice"))

                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    # Fallback: stream an error message
                    fallback = "I apologize, I'm having trouble right now. Please try again."
                    await stream_text_to_retell(ws, fallback, response_id)

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Clean up the mapping
        if call_id:
            delete_call_mapping(call_id)
        logger.info(f"Call ended: {customer_id}")
        await ws.close()

    return ws


# === Application Setup ===

async def on_shutdown(app):
    """Cleanup on shutdown."""
    await close_http_client()
    logger.info("Server shutdown complete")


def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()

    # Core routes
    app.router.add_route("GET", "/health", health)
    app.router.add_route("POST", "/create-call", create_call)
    app.router.add_route("OPTIONS", "/create-call", create_call)
    app.router.add_route("POST", "/chat", chat)
    app.router.add_route("OPTIONS", "/chat", chat)
    app.router.add_route("GET", "/llm-websocket/{call_id}", llm_websocket)

    # Analytics API routes
    app.router.add_route("GET", "/api/analytics/stats", api_analytics_stats)
    app.router.add_route("OPTIONS", "/api/analytics/stats", api_analytics_stats)
    app.router.add_route("GET", "/api/analytics/conversations", api_analytics_conversations)
    app.router.add_route("OPTIONS", "/api/analytics/conversations", api_analytics_conversations)

    # Domain management API routes
    app.router.add_route("GET", "/api/domains", api_domains_list)
    app.router.add_route("POST", "/api/domains", api_domain_create)
    app.router.add_route("PUT", "/api/domains", api_domain_update)
    app.router.add_route("OPTIONS", "/api/domains", api_domains_list)  # Single OPTIONS handler

    # Voice API
    app.router.add_route("GET", "/api/voices", api_voices_list)
    app.router.add_route("OPTIONS", "/api/voices", api_voices_list)

    # Static files - serve frontend from parent directory
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "..")

    # Serve specific HTML files
    async def serve_file(request: web.Request, filename: str) -> web.StreamResponse:
        filepath = os.path.join(static_dir, filename)
        if os.path.exists(filepath):
            return web.FileResponse(filepath)
        return web.Response(text="Not found", status=404)

    app.router.add_route("GET", "/", lambda r: serve_file(r, "landing.html"))
    app.router.add_route("GET", "/index.html", lambda r: serve_file(r, "index.html"))
    app.router.add_route("GET", "/landing.html", lambda r: serve_file(r, "landing.html"))
    app.router.add_route("GET", "/admin.html", lambda r: serve_file(r, "admin.html"))
    app.router.add_route("GET", "/widget.js", lambda r: serve_file(r, "widget.js"))
    app.router.add_route("GET", "/widget-demo.html", lambda r: serve_file(r, "widget-demo.html"))

    # Register shutdown handler
    app.on_shutdown.append(on_shutdown)

    return app


async def main():
    """Main entry point."""
    logger.info("Starting Omni AI server on port 8080...")
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Server started successfully")
    await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
