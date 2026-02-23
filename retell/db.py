"""
Database operations for Omni AI using Supabase.
"""
from typing import Optional
from supabase import create_client, Client

from .config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    HISTORY_LIMIT,
    logger
)

# Initialize Supabase client
_supabase: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get or create Supabase client instance."""
    global _supabase
    if _supabase is None and SUPABASE_URL and SUPABASE_KEY:
        try:
            _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
    return _supabase


def _role_to_openai(role: str) -> str:
    """Convert role to OpenAI format."""
    if role in ("agent", "assistant"):
        return "assistant"
    return "user"


def get_customer_messages(customer_id: str, limit: int = HISTORY_LIMIT) -> list[dict]:
    """
    Returns last messages in OpenAI format: [{"role": "...", "content": "..."}]
    """
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase not configured, returning empty history")
        return []

    try:
        result = supabase.table("player_sessions") \
            .select("*") \
            .eq("player_id", customer_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        if not result.data:
            return []

        # Supabase returns newest first; reverse to chronological
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
        logger.error(f"Supabase error (get_customer_messages): {e}")
        return []


def get_customer_context(customer_id: str) -> str:
    """Get formatted conversation history for context."""
    supabase = get_supabase()
    if not supabase:
        return "No previous interaction history."

    try:
        result = supabase.table("player_sessions") \
            .select("*") \
            .eq("player_id", customer_id) \
            .order("created_at", desc=True) \
            .limit(HISTORY_LIMIT) \
            .execute()

        if not result.data:
            return "No previous interaction history."

        history = []
        for row in reversed(result.data):
            history.append(f"{row['role']} ({row['channel']}): {row['message']}")

        return "\n".join(history)
    except Exception as e:
        logger.error(f"Supabase error (get_customer_context): {e}")
        return "No previous interaction history."


def save_message(customer_id: str, role: str, message: str, channel: str = "voice") -> bool:
    """Save a message to the database. Returns True on success."""
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase not configured, message not saved")
        return False

    try:
        supabase.table("player_sessions").insert({
            "player_id": customer_id,
            "channel": channel,
            "role": role,
            "message": message
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Supabase error (save_message): {e}")
        return False


# === Call-Customer Mapping (stored in Supabase for persistence) ===

def store_call_mapping(call_id: str, customer_id: str) -> bool:
    """Store call_id to customer_id mapping in database."""
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase not configured, call mapping not stored")
        return False

    try:
        # Use upsert to handle duplicate call_ids
        supabase.table("call_mappings").upsert({
            "call_id": call_id,
            "customer_id": customer_id
        }, on_conflict="call_id").execute()
        logger.info(f"Stored call mapping: {call_id} -> {customer_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to store call mapping: {e}")
        return False


def get_call_mapping(call_id: str) -> Optional[str]:
    """Get customer_id for a call_id from database."""
    supabase = get_supabase()
    if not supabase:
        return None

    try:
        result = supabase.table("call_mappings") \
            .select("customer_id") \
            .eq("call_id", call_id) \
            .limit(1) \
            .execute()

        if result.data:
            return result.data[0].get("customer_id")
        return None
    except Exception as e:
        logger.error(f"Failed to get call mapping: {e}")
        return None


def delete_call_mapping(call_id: str) -> bool:
    """Delete call mapping when call ends."""
    supabase = get_supabase()
    if not supabase:
        return False

    try:
        supabase.table("call_mappings") \
            .delete() \
            .eq("call_id", call_id) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete call mapping: {e}")
        return False
