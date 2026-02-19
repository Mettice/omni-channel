import os
import json
import asyncio
from aiohttp import web
from supabase import create_client

# Load env vars from .env (supports running from /retell)
def _load_dotenv_fallback() -> str | None:
    candidates = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]

    for p in candidates:
        try:
            if not os.path.exists(p):
                continue

            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k:
                        os.environ.setdefault(k, v)
            return p
        except Exception:
            continue

    return None

_ENV_PATH = _load_dotenv_fallback()
if _ENV_PATH:
    print(f"Loaded environment from: {_ENV_PATH}")

RETELL_AGENT_ID = "agent_f604bb54a90edd0d700a3b40ca"

# Supabase config
SUPABASE_URL = "https://dsoywpytpvxqpxiugopq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzb3l3cHl0cHZ4cXB4aXVnb3BxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzODM4NTMsImV4cCI6MjA4Njk1OTg1M30.B4wEnUp80TCpKpesWTcKj8Q3YbL-Q-LeIGEhmXdUrMs"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# In-memory mapping of Retell call_id -> customer_id
# (For production, use Redis or database)
CALL_CUSTOMER_MAP = {}

# n8n Webhook URLs (configure per client)
N8N_WEBHOOK_BASE = os.environ.get("N8N_WEBHOOK_BASE", "")  # e.g., "https://your-n8n.com/webhook"

# Domain/Industry configuration (loaded from environment or config file)
DOMAIN = os.environ.get("DOMAIN", "generic")  # e.g., "igaming", "ecommerce", "healthcare", "fintech"

# System prompts per domain
SYSTEM_PROMPTS = {
    "igaming": """You are a professional customer support agent.
Keep responses under 2 sentences. Be warm, professional, and concise.
Help customers with their inquiries efficiently.""",

    "ecommerce": """You are a friendly e-commerce customer support agent.
Keep responses under 2 sentences. Be helpful and solution-oriented.
Help with: orders, shipping, returns, refunds, product questions, account issues.""",

    "healthcare": """You are a professional healthcare scheduling assistant.
Keep responses under 2 sentences. Be empathetic and clear.
Help with: appointments, scheduling, prescription refills, general inquiries.
Never provide medical advice - always direct to healthcare providers.""",

    "fintech": """You are a professional banking support assistant.
Keep responses under 2 sentences. Be secure-minded and precise.
Help with: account inquiries, transactions, card issues, payments.
Never share or ask for full account numbers or passwords.""",

    "realestate": """You are a professional real estate assistant.
Keep responses under 2 sentences. Be knowledgeable and helpful.
Help with: property inquiries, scheduling viewings, pricing questions, neighborhood info.""",

    "generic": """You are a professional customer support agent.
Keep responses under 2 sentences. Be warm, professional, and concise.
Help customers with their inquiries efficiently.
You have access to the conversation history - use it to provide personalized, contextual responses."""
}

# Intent patterns per domain (configurable per industry)
DOMAIN_INTENTS = {
    "igaming": {
        "escalate": {
            "keywords": ["manager", "human", "supervisor", "complaint", "speak to someone", "real person"],
            "webhook": "/escalate"
        },
        "withdrawal": {
            "keywords": ["withdraw", "withdrawal", "cash out", "payout", "my money"],
            "webhook": "/withdrawal-status"
        },
        "bonus": {
            "keywords": ["bonus", "promotion", "free spins", "offer", "reward"],
            "webhook": "/bonus-status"
        },
        "verification": {
            "keywords": ["verify", "verification", "kyc", "documents", "id", "identity"],
            "webhook": "/verification-status"
        }
    },
    "ecommerce": {
        "escalate": {
            "keywords": ["manager", "human", "supervisor", "complaint", "speak to someone"],
            "webhook": "/escalate"
        },
        "order_status": {
            "keywords": ["where is my order", "track", "shipping", "delivery", "package"],
            "webhook": "/order-status"
        },
        "return": {
            "keywords": ["return", "refund", "exchange", "send back", "money back"],
            "webhook": "/return-request"
        },
        "cancel": {
            "keywords": ["cancel", "cancel order", "don't want", "stop order"],
            "webhook": "/cancel-order"
        }
    },
    "healthcare": {
        "escalate": {
            "keywords": ["doctor", "nurse", "emergency", "urgent", "speak to someone"],
            "webhook": "/escalate"
        },
        "appointment": {
            "keywords": ["appointment", "schedule", "book", "available", "see doctor", "visit"],
            "webhook": "/appointment"
        },
        "prescription": {
            "keywords": ["prescription", "refill", "medication", "medicine", "pharmacy"],
            "webhook": "/prescription"
        },
        "results": {
            "keywords": ["results", "test results", "lab", "report"],
            "webhook": "/results"
        }
    },
    "fintech": {
        "escalate": {
            "keywords": ["manager", "human", "supervisor", "complaint", "fraud", "unauthorized"],
            "webhook": "/escalate"
        },
        "balance": {
            "keywords": ["balance", "how much", "available", "account balance"],
            "webhook": "/balance"
        },
        "transaction": {
            "keywords": ["transaction", "payment", "transfer", "sent", "received"],
            "webhook": "/transaction"
        },
        "card": {
            "keywords": ["card", "lost card", "stolen", "block card", "new card"],
            "webhook": "/card-issue"
        }
    },
    "realestate": {
        "escalate": {
            "keywords": ["manager", "human", "agent", "speak to someone"],
            "webhook": "/escalate"
        },
        "viewing": {
            "keywords": ["view", "visit", "see property", "tour", "showing", "schedule"],
            "webhook": "/schedule-viewing"
        },
        "pricing": {
            "keywords": ["price", "cost", "how much", "afford", "mortgage", "financing"],
            "webhook": "/pricing-inquiry"
        },
        "availability": {
            "keywords": ["available", "still available", "sold", "rent", "lease"],
            "webhook": "/availability"
        }
    },
    "generic": {
        "escalate": {
            "keywords": ["manager", "human", "supervisor", "complaint", "speak to someone", "real person"],
            "webhook": "/escalate"
        }
    }
}

def get_system_prompt(player_id: str = "", context: str = "") -> str:
    """Get the system prompt for the current domain."""
    base_prompt = SYSTEM_PROMPTS.get(DOMAIN, SYSTEM_PROMPTS["generic"])
    if context:
        return f"{base_prompt}\n\nCustomer history:\n{context}"
    return base_prompt

def get_intent_patterns() -> dict:
    """Get intent patterns for the current domain."""
    return DOMAIN_INTENTS.get(DOMAIN, DOMAIN_INTENTS["generic"])

# Greetings per domain
DOMAIN_GREETINGS = {
    "igaming": "Hello! Welcome to support. How can I help you today?",
    "ecommerce": "Hi there! Thanks for calling. How can I help with your order today?",
    "healthcare": "Hello, thank you for calling. How may I assist you with your healthcare needs today?",
    "fintech": "Welcome to support. How can I assist you with your account today?",
    "realestate": "Hi! Thanks for reaching out. Are you looking to buy, sell, or rent today?",
    "generic": "Hello! How can I assist you today?"
}

def get_greeting() -> str:
    """Get the greeting for the current domain."""
    return DOMAIN_GREETINGS.get(DOMAIN, DOMAIN_GREETINGS["generic"])


async def detect_and_trigger_intents(customer_id: str, message: str, channel: str = "voice") -> dict:
    """
    Detect intents in message and trigger corresponding n8n webhooks.
    Returns dict of triggered intents and their responses.
    """
    if not N8N_WEBHOOK_BASE:
        return {}

    import httpx

    message_lower = message.lower()
    triggered = {}
    intent_patterns = get_intent_patterns()

    for intent_name, config in intent_patterns.items():
        if any(keyword in message_lower for keyword in config["keywords"]):
            webhook_url = f"{N8N_WEBHOOK_BASE}{config['webhook']}"
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        webhook_url,
                        json={
                            "customer_id": customer_id,
                            "message": message,
                            "channel": channel,
                            "intent": intent_name,
                            "domain": DOMAIN
                        },
                        timeout=5
                    )
                    if res.status_code == 200:
                        triggered[intent_name] = res.text
                        print(f"[{DOMAIN}] Triggered intent '{intent_name}' for customer {customer_id}")
            except Exception as e:
                print(f"n8n webhook error ({intent_name}): {e}")

    return triggered


def _role_to_openai(role: str) -> str:
    if role == "agent":
        return "assistant"
    if role == "assistant":
        return "assistant"
    return "user"


def get_player_messages(player_id: str, limit: int = 10) -> list[dict]:
    """
    Returns last messages in OpenAI format: [{"role": "...", "content": "..."}]
    """
    try:
        result = supabase.table("player_sessions") \
            .select("*") \
            .eq("player_id", player_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        if not result.data:
            return []

        # Supabase returns newest first; reverse to chronological.
        msgs = []
        for row in reversed(result.data):
            content = row.get("message") or ""
            if not content:
                continue
            msgs.append({
                "role": _role_to_openai(row.get("role", "user")),
                "content": content
            })
        return msgs
    except Exception as e:
        print(f"Supabase error (messages): {e}")
        return []

def get_player_context(player_id: str) -> str:
    try:
        result = supabase.table("player_sessions") \
            .select("*") \
            .eq("player_id", player_id) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        
        if not result.data:
            return "No previous interaction history."
        
        history = []
        for row in reversed(result.data):
            history.append(f"{row['role']} ({row['channel']}): {row['message']}")
        
        return "\n".join(history)
    except Exception as e:
        print(f"Supabase error: {e}")
        return "No previous interaction history."

def save_message(player_id: str, role: str, message: str, channel: str = "voice"):
    try:
        supabase.table("player_sessions").insert({
            "player_id": player_id,
            "channel": channel,
            "role": role,
            "message": message
        }).execute()
    except Exception as e:
        print(f"Save error: {e}")

async def generate_response(messages: list) -> str:
    """Non-streaming version for chat endpoint."""
    import httpx

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set (check your .env loading).")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 150
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )

        # If the API returns an error payload, it won't contain "choices"
        try:
            data = res.json()
        except Exception:
            raise RuntimeError(f"OpenAI returned non-JSON response (HTTP {res.status_code}).")

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
    Streaming version for Retell Custom LLM.
    Streams tokens directly to the WebSocket and returns the full response.
    """
    import httpx

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set (check your .env loading).")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 150,
        "stream": True
    }

    full_response = ""

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
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

    # Send completion signal to Retell
    await ws.send_str(json.dumps({
        "response_id": response_id,
        "content": "",
        "content_complete": True
    }))

    return full_response

def _corsify(resp: web.StreamResponse) -> web.StreamResponse:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


async def create_call(request: web.Request) -> web.StreamResponse:
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    retell_api_key = os.environ.get("RETELL_API_KEY")
    if not retell_api_key:
        return _corsify(web.json_response({"error": "RETELL_API_KEY is not set"}, status=500))

    # Get customer_id from query string
    customer_id = request.query.get("customer_id", "unknown")
    print(f"Creating call for customer: {customer_id}")

    payload = {
        "agent_id": RETELL_AGENT_ID,
        "metadata": {"customer_id": customer_id}
    }
    headers = {
        "Authorization": f"Bearer {retell_api_key}",
        "Content-Type": "application/json",
    }

    import aiohttp
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
                    return _corsify(web.json_response({"error": data}, status=resp.status))

                access_token = data.get("access_token")
                call_id = data.get("call_id")

                if not access_token:
                    return _corsify(web.json_response({"error": "Missing access_token", "data": data}, status=500))

                # Store mapping of call_id -> customer_id
                if call_id:
                    CALL_CUSTOMER_MAP[call_id] = customer_id
                    print(f"Mapped call {call_id} -> customer {customer_id}")

                return _corsify(web.json_response({"access_token": access_token}))
    except Exception as e:
        return _corsify(web.json_response({"error": str(e)}, status=500))


async def chat(request: web.Request) -> web.StreamResponse:
    if request.method == "OPTIONS":
        return _corsify(web.Response(status=204))

    try:
        payload = await request.json()
    except Exception:
        return _corsify(web.json_response({"error": "Invalid JSON body"}, status=400))

    player_id = payload.get("player_id")
    message = payload.get("message")
    if not player_id or not isinstance(player_id, str):
        return _corsify(web.json_response({"error": "player_id is required"}, status=400))
    if not message or not isinstance(message, str):
        return _corsify(web.json_response({"error": "message is required"}, status=400))

    # Persist user message first
    save_message(player_id, "user", message, channel="web")

    history = get_player_messages(player_id, limit=10)

    try:
        response = await generate_response(
            [{"role": "system", "content": get_system_prompt()}]
            + history
            + [{"role": "user", "content": message}]
        )
    except Exception as e:
        print(f"Chat generation failed: {e}")
        return _corsify(web.json_response({"error": str(e)}, status=500))

    save_message(player_id, "agent", response, channel="web")

    # Trigger n8n workflows based on detected intents (runs in background)
    asyncio.create_task(detect_and_trigger_intents(player_id, message, "chat"))

    return _corsify(web.json_response({"response": response}))


async def stream_text_to_retell(ws, text: str, response_id: int):
    """
    Stream a pre-generated text to Retell token by token.
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
        # Small delay to simulate natural speech pacing
        await asyncio.sleep(0.05)

    # Send completion signal
    await ws.send_str(json.dumps({
        "response_id": response_id,
        "content": "",
        "content_complete": True
    }))


async def llm_websocket(request: web.Request) -> web.StreamResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    call_id = request.match_info.get("call_id", "unknown")

    # Look up customer_id from our mapping
    customer_id = CALL_CUSTOMER_MAP.get(call_id, call_id)
    print(f"=== NEW CALL ===")
    print(f"Call ID: {call_id}")
    print(f"Customer ID: {customer_id}")

    # Load history for this customer
    history = get_player_messages(customer_id, limit=10)
    print(f"Loaded {len(history)} messages from history")

    # Track if we've sent initial greeting
    greeting_sent = False

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
            print(f"Received event: {interaction_type}")
            print(f"Full data: {json.dumps(data)[:300]}")

            if interaction_type == "call_details":
                # We already have customer_id from the mapping, just log
                print(f"Received call_details event")
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
                transcript = data.get("transcript", [])

                # Find the last user message
                last_user_msg = ""
                for t in reversed(transcript):
                    if t.get("role") == "user":
                        last_user_msg = t.get("content", "")
                        break

                # If no user message yet, send greeting
                if not last_user_msg and not greeting_sent:
                    greeting = get_greeting()
                    print(f"Streaming greeting to {cid}: {greeting}")
                    await stream_text_to_retell(ws, greeting, response_id)
                    save_message(customer_id, "agent", greeting)
                    greeting_sent = True
                    continue

                # Get conversation history BEFORE saving new message
                history = get_player_messages(customer_id, limit=10)
                print(f"History loaded for {cid}: {len(history)} messages")

                if last_user_msg:
                    save_message(customer_id, "user", last_user_msg)
                    greeting_sent = True  # User spoke, so greeting phase is over

                prompt = last_user_msg if last_user_msg else "greet the customer warmly"

                print(f"Generating streaming response for {customer_id}: {prompt[:50]}...")

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
                    print(f"Streamed response: {response}")
                    save_message(customer_id, "agent", response)

                    # Trigger n8n workflows based on detected intents (runs in background)
                    asyncio.create_task(detect_and_trigger_intents(customer_id, last_user_msg, "voice"))
                except Exception as e:
                    print(f"Streaming error: {e}")
                    # Fallback: stream an error message
                    fallback = "I apologize, I'm having trouble right now. Please try again."
                    await stream_text_to_retell(ws, fallback, response_id)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up the mapping
        if call_id in CALL_CUSTOMER_MAP:
            del CALL_CUSTOMER_MAP[call_id]
        print(f"Call ended: {customer_id}")
        await ws.close()

    return ws


async def main():
    print("Starting Retell LLM WebSocket + HTTP server on port 8080...")
    app = web.Application()
    app.router.add_route("POST", "/create-call", create_call)
    app.router.add_route("OPTIONS", "/create-call", create_call)
    app.router.add_route("POST", "/chat", chat)
    app.router.add_route("OPTIONS", "/chat", chat)
    app.router.add_route("GET", "/llm-websocket/{call_id}", llm_websocket)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())