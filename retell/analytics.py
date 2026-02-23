"""
Analytics and metrics tracking for Omni AI.

Tracks conversations, intents, response times, and other key metrics.
Stores data in Supabase for persistence and dashboard access.
"""
import time
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict

from .db import get_supabase
from .config import DOMAIN, logger


@dataclass
class ConversationMetrics:
    """Metrics for a single conversation."""
    customer_id: str
    channel: str  # voice, chat, widget
    domain: str
    start_time: str
    end_time: Optional[str] = None
    message_count: int = 0
    avg_response_time_ms: float = 0
    intents_detected: list = None
    escalated: bool = False
    resolved: bool = False

    def __post_init__(self):
        if self.intents_detected is None:
            self.intents_detected = []


@dataclass
class MessageMetrics:
    """Metrics for a single message."""
    customer_id: str
    channel: str
    role: str  # user, agent
    timestamp: str
    response_time_ms: Optional[float] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    token_count: Optional[int] = None


# In-memory tracking for active conversations
_active_conversations: dict[str, dict] = {}


def start_conversation(customer_id: str, channel: str) -> None:
    """Mark the start of a conversation for metrics tracking."""
    _active_conversations[customer_id] = {
        "start_time": datetime.now(timezone.utc).isoformat(),
        "channel": channel,
        "message_count": 0,
        "response_times": [],
        "intents": [],
        "last_message_time": time.time()
    }
    logger.debug(f"Started tracking conversation for {customer_id}")


def track_message(
    customer_id: str,
    role: str,
    channel: str = "chat",
    response_time_ms: float = None,
    intent: str = None,
    intent_confidence: float = None
) -> None:
    """Track a message in the current conversation."""
    now = time.time()

    # Initialize if not exists
    if customer_id not in _active_conversations:
        start_conversation(customer_id, channel)

    conv = _active_conversations[customer_id]
    conv["message_count"] += 1

    if response_time_ms is not None:
        conv["response_times"].append(response_time_ms)

    if intent:
        conv["intents"].append({
            "intent": intent,
            "confidence": intent_confidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    conv["last_message_time"] = now

    # Also save to database
    _save_message_metric(customer_id, role, channel, response_time_ms, intent, intent_confidence)


def track_intent(
    customer_id: str,
    intent: str,
    confidence: float,
    webhook_triggered: bool = False
) -> None:
    """Track an intent detection event."""
    supabase = get_supabase()
    if not supabase:
        return

    try:
        supabase.table("analytics_intents").insert({
            "customer_id": customer_id,
            "intent": intent,
            "confidence": confidence,
            "webhook_triggered": webhook_triggered,
            "domain": DOMAIN,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"Failed to track intent: {e}")


def end_conversation(customer_id: str, resolved: bool = True) -> Optional[dict]:
    """
    Mark end of conversation and calculate final metrics.
    Returns the conversation summary.
    """
    if customer_id not in _active_conversations:
        return None

    conv = _active_conversations.pop(customer_id)

    # Calculate metrics
    end_time = datetime.now(timezone.utc).isoformat()
    avg_response_time = (
        sum(conv["response_times"]) / len(conv["response_times"])
        if conv["response_times"] else 0
    )

    escalated = any(i["intent"] == "escalate" for i in conv["intents"])

    metrics = ConversationMetrics(
        customer_id=customer_id,
        channel=conv["channel"],
        domain=DOMAIN,
        start_time=conv["start_time"],
        end_time=end_time,
        message_count=conv["message_count"],
        avg_response_time_ms=avg_response_time,
        intents_detected=[i["intent"] for i in conv["intents"]],
        escalated=escalated,
        resolved=resolved
    )

    # Save to database
    _save_conversation_metric(metrics)

    return asdict(metrics)


def _save_message_metric(
    customer_id: str,
    role: str,
    channel: str,
    response_time_ms: float = None,
    intent: str = None,
    intent_confidence: float = None
) -> None:
    """Save message metric to database."""
    supabase = get_supabase()
    if not supabase:
        return

    try:
        supabase.table("analytics_messages").insert({
            "customer_id": customer_id,
            "channel": channel,
            "role": role,
            "response_time_ms": response_time_ms,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "domain": DOMAIN,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"Failed to save message metric: {e}")


def _save_conversation_metric(metrics: ConversationMetrics) -> None:
    """Save conversation metric to database."""
    supabase = get_supabase()
    if not supabase:
        return

    try:
        data = asdict(metrics)
        # Convert list to JSON string for storage
        data["intents_detected"] = ",".join(data["intents_detected"])
        supabase.table("analytics_conversations").insert(data).execute()
        logger.info(f"Saved conversation metrics for {metrics.customer_id}")
    except Exception as e:
        logger.error(f"Failed to save conversation metric: {e}")


# === Dashboard Query Functions ===

async def get_dashboard_stats(days: int = 7) -> dict:
    """Get aggregated stats for the dashboard."""
    supabase = get_supabase()
    if not supabase:
        return {}

    try:
        # Get conversation stats
        conv_result = supabase.table("analytics_conversations") \
            .select("*") \
            .gte("start_time", f"now() - interval '{days} days'") \
            .execute()

        conversations = conv_result.data or []

        # Calculate aggregates
        total_conversations = len(conversations)
        total_messages = sum(c.get("message_count", 0) for c in conversations)
        avg_response_time = (
            sum(c.get("avg_response_time_ms", 0) for c in conversations) / total_conversations
            if total_conversations > 0 else 0
        )
        escalation_rate = (
            sum(1 for c in conversations if c.get("escalated")) / total_conversations * 100
            if total_conversations > 0 else 0
        )
        resolution_rate = (
            sum(1 for c in conversations if c.get("resolved")) / total_conversations * 100
            if total_conversations > 0 else 0
        )

        # Channel breakdown
        channels = {}
        for c in conversations:
            channel = c.get("channel", "unknown")
            channels[channel] = channels.get(channel, 0) + 1

        # Intent breakdown
        intents = {}
        for c in conversations:
            for intent in (c.get("intents_detected") or "").split(","):
                if intent:
                    intents[intent] = intents.get(intent, 0) + 1

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "avg_response_time_ms": round(avg_response_time, 2),
            "escalation_rate": round(escalation_rate, 1),
            "resolution_rate": round(resolution_rate, 1),
            "channels": channels,
            "top_intents": dict(sorted(intents.items(), key=lambda x: x[1], reverse=True)[:5]),
            "period_days": days
        }

    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        return {}


async def get_conversations_list(
    limit: int = 50,
    offset: int = 0,
    channel: str = None
) -> list[dict]:
    """Get list of recent conversations for dashboard."""
    supabase = get_supabase()
    if not supabase:
        return []

    try:
        query = supabase.table("analytics_conversations") \
            .select("*") \
            .order("start_time", desc=True) \
            .range(offset, offset + limit - 1)

        if channel:
            query = query.eq("channel", channel)

        result = query.execute()
        return result.data or []

    except Exception as e:
        logger.error(f"Failed to get conversations list: {e}")
        return []


async def get_hourly_traffic(hours: int = 24) -> list[dict]:
    """Get conversation counts by hour for charts."""
    supabase = get_supabase()
    if not supabase:
        return []

    try:
        # This would need a custom SQL function for proper hourly grouping
        # For now, return raw data that can be grouped client-side
        result = supabase.table("analytics_conversations") \
            .select("start_time,channel") \
            .gte("start_time", f"now() - interval '{hours} hours'") \
            .order("start_time") \
            .execute()

        return result.data or []

    except Exception as e:
        logger.error(f"Failed to get hourly traffic: {e}")
        return []
