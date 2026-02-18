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

    payload = {"agent_id": RETELL_AGENT_ID}
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
                if not access_token:
                    return _corsify(web.json_response({"error": "Missing access_token", "data": data}, status=500))

                return _corsify(web.json_response({"access_token": access_token}))
    except Exception as e:
        return _corsify(web.json_response({"error": str(e)}, status=500))


async def llm_websocket(request: web.Request) -> web.StreamResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    call_id = request.match_info.get("call_id", "unknown")
    print("New call connected")
    print(f"Call ID: {call_id}")

    context = get_player_context(call_id)
    print(f"Context loaded: {context[:100]}")

    # Small delay before first send (Retell timing)
    await asyncio.sleep(1)

    greeting = "Hello! Welcome to Casino Support. How can I help you today?"
    print(f"Sending greeting: {greeting}")
    try:
        await ws.send_str(json.dumps({
            "response_id": 0,
            "response_type": "response",
            "transcript": [{"role": "agent", "content": greeting}],
        }))
    except Exception as e:
        print(f"Failed to send greeting: {e}")

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
            print(f"Received event: {interaction_type}")
            print(f"Full data: {json.dumps(data)[:300]}")

            if interaction_type in ["call_started", "response_required"]:
                response_id = data.get("response_id", 0)
                transcript = data.get("transcript", [])

                last_user_msg = ""
                for t in reversed(transcript):
                    if t.get("role") == "user":
                        last_user_msg = t.get("content", "")
                        break

                if last_user_msg:
                    save_message(call_id, "user", last_user_msg)

                prompt = last_user_msg if last_user_msg else "greet the player warmly"

                # Refresh context each turn to include newly saved messages
                context = get_player_context(call_id)

                response = await generate_response([
                    {
                        "role": "system",
                        "content": f"""You are a professional iGaming voice support agent.
Keep responses under 2 sentences.
Player history:
{context}"""
                    },
                    {"role": "user", "content": prompt}
                ])

                print(f"Sending response: {response}")
                save_message(call_id, "agent", response)

                await ws.send_str(json.dumps({
                    "response_id": response_id,
                    "response_type": "response",
                    "transcript": [{"role": "agent", "content": response}],
                }))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"Call ended: {call_id}")
        await ws.close()

    return ws


async def main():
    print("Starting Retell LLM WebSocket + HTTP server on port 8080...")
    app = web.Application()
    app.router.add_route("POST", "/create-call", create_call)
    app.router.add_route("OPTIONS", "/create-call", create_call)
    app.router.add_route("GET", "/llm-websocket/{call_id}", llm_websocket)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())