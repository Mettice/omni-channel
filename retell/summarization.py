"""
Conversation summarization for long sessions.

This module handles summarizing long conversation histories to fit within
context limits while preserving important information.
"""
import httpx
from typing import Optional

from .config import OPENAI_API_KEY, HISTORY_LIMIT, logger

# Summarization settings
MAX_MESSAGES_BEFORE_SUMMARY = 20  # Trigger summarization after this many messages
SUMMARY_KEEP_RECENT = 5  # Always keep this many recent messages unsummarized
MAX_TOKENS_FOR_SUMMARY = 500  # Max tokens for the summary
SUMMARY_MODEL = "gpt-4o-mini"  # Use cheaper model for summarization


async def summarize_conversation(messages: list[dict]) -> Optional[str]:
    """
    Summarize a list of conversation messages into a concise summary.

    Args:
        messages: List of {"role": "user/assistant", "content": "..."} dicts

    Returns:
        Summary string or None if summarization fails
    """
    if not OPENAI_API_KEY or not messages:
        return None

    # Format messages for summarization
    conversation_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in messages
    ])

    summary_prompt = f"""Summarize this customer support conversation concisely.
Focus on:
- Customer's main issue or request
- Any important details shared (names, account info, preferences)
- What has been resolved or discussed
- Any pending actions or commitments

Keep the summary under 200 words. Write in third person (e.g., "The customer asked about...").

CONVERSATION:
{conversation_text}

SUMMARY:"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": SUMMARY_MODEL,
                    "messages": [
                        {"role": "user", "content": summary_prompt}
                    ],
                    "max_tokens": MAX_TOKENS_FOR_SUMMARY,
                    "temperature": 0.3  # Lower temperature for more consistent summaries
                },
                timeout=15
            )

            if response.status_code != 200:
                logger.error(f"Summarization API error: {response.status_code}")
                return None

            data = response.json()
            summary = data["choices"][0]["message"]["content"]
            logger.info(f"Summarized {len(messages)} messages into {len(summary)} chars")
            return summary

    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return None


async def get_condensed_history(
    messages: list[dict],
    max_messages: int = MAX_MESSAGES_BEFORE_SUMMARY,
    keep_recent: int = SUMMARY_KEEP_RECENT
) -> list[dict]:
    """
    Get a condensed version of conversation history.

    If the conversation is short, returns all messages.
    If long, summarizes older messages and keeps recent ones intact.

    Args:
        messages: Full conversation history
        max_messages: Trigger summarization if more than this
        keep_recent: Always keep this many recent messages

    Returns:
        List of messages with potential summary prepended
    """
    if len(messages) <= max_messages:
        return messages

    # Split into old messages (to summarize) and recent (to keep)
    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]

    # Summarize old messages
    summary = await summarize_conversation(old_messages)

    if summary:
        # Return summary as a system message followed by recent messages
        return [
            {
                "role": "system",
                "content": f"[Previous conversation summary: {summary}]"
            }
        ] + recent_messages
    else:
        # Fallback: just return recent messages if summarization failed
        logger.warning("Summarization failed, using truncated history")
        return recent_messages


def estimate_tokens(messages: list[dict]) -> int:
    """
    Rough estimate of token count for messages.
    Uses ~4 chars per token as approximation.
    """
    total_chars = sum(len(msg.get("content", "")) for msg in messages)
    return total_chars // 4


async def smart_context_management(
    messages: list[dict],
    max_context_tokens: int = 4000
) -> list[dict]:
    """
    Intelligently manage context to stay within token limits.

    Args:
        messages: Full conversation history
        max_context_tokens: Maximum tokens to allow for history

    Returns:
        Optimized message list
    """
    current_tokens = estimate_tokens(messages)

    if current_tokens <= max_context_tokens:
        return messages

    logger.info(f"Context too large ({current_tokens} tokens), condensing...")

    # Try condensing with summarization
    condensed = await get_condensed_history(messages)
    new_tokens = estimate_tokens(condensed)

    if new_tokens <= max_context_tokens:
        logger.info(f"Condensed to {new_tokens} tokens")
        return condensed

    # If still too large, be more aggressive
    # Keep only the summary and last 3 messages
    if len(condensed) > 4:
        aggressive_condensed = condensed[:1] + condensed[-3:]
        logger.warning(f"Aggressive condensation: {len(messages)} -> {len(aggressive_condensed)} messages")
        return aggressive_condensed

    return condensed
