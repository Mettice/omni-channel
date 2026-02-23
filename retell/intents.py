"""
Intent detection and n8n webhook integration for Omni AI.
"""
import httpx

from .config import (
    N8N_WEBHOOK_BASE,
    DOMAIN,
    WEBHOOK_TIMEOUT,
    get_intent_patterns,
    logger
)


async def detect_and_trigger_intents(
    customer_id: str,
    message: str,
    channel: str = "voice"
) -> dict:
    """
    Detect intents in message and trigger corresponding n8n webhooks.

    Args:
        customer_id: Customer identifier
        message: User message to analyze
        channel: Channel type (voice/chat/web)

    Returns:
        Dict of triggered intents and their responses
    """
    if not N8N_WEBHOOK_BASE:
        return {}

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
                        timeout=WEBHOOK_TIMEOUT
                    )
                    if res.status_code == 200:
                        triggered[intent_name] = res.text
                        logger.info(f"[{DOMAIN}] Triggered intent '{intent_name}' for customer {customer_id}")
                    else:
                        logger.warning(f"Webhook returned {res.status_code} for intent '{intent_name}'")
            except httpx.TimeoutException:
                logger.warning(f"Webhook timeout for intent '{intent_name}'")
            except httpx.RequestError as e:
                logger.error(f"Webhook error ({intent_name}): {e}")

    return triggered
