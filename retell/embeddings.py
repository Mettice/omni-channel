"""
Semantic intent detection using OpenAI embeddings.

This module provides NLP-based intent detection that's more robust than keyword matching.
It uses cosine similarity between user message embeddings and pre-computed intent embeddings.
"""
import json
import numpy as np
from typing import Optional
import httpx

from .config import OPENAI_API_KEY, DOMAIN, logger

# Embedding model - text-embedding-3-small is fast and cheap
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Intent definitions with example phrases for each domain
# These examples are used to create intent embeddings
INTENT_EXAMPLES = {
    "igaming": {
        "escalate": {
            "examples": [
                "I want to speak to a manager",
                "Let me talk to a human",
                "I need a supervisor",
                "This is unacceptable, I want to complain",
                "Connect me to a real person",
                "I'm not satisfied with this response",
                "I demand to speak with someone in charge"
            ],
            "webhook": "/escalate",
            "threshold": 0.75
        },
        "withdrawal": {
            "examples": [
                "I want to withdraw my money",
                "How do I cash out my winnings",
                "When will I get my payout",
                "My withdrawal is pending",
                "I need to take out my balance",
                "Transfer my winnings to my bank",
                "How long does withdrawal take"
            ],
            "webhook": "/withdrawal-status",
            "threshold": 0.78
        },
        "bonus": {
            "examples": [
                "What bonuses do I have",
                "I want to claim a promotion",
                "Are there any free spins available",
                "Tell me about current offers",
                "How do I get the welcome bonus",
                "My bonus didn't apply",
                "What rewards can I get"
            ],
            "webhook": "/bonus-status",
            "threshold": 0.76
        },
        "verification": {
            "examples": [
                "How do I verify my account",
                "What documents do you need",
                "My KYC is taking too long",
                "I uploaded my ID but nothing happened",
                "Identity verification process",
                "Why is my account not verified",
                "What ID do you accept"
            ],
            "webhook": "/verification-status",
            "threshold": 0.77
        }
    },
    "ecommerce": {
        "escalate": {
            "examples": [
                "I want to speak to a manager",
                "Let me talk to a human",
                "I need a supervisor",
                "This is unacceptable",
                "I want to file a complaint"
            ],
            "webhook": "/escalate",
            "threshold": 0.75
        },
        "order_status": {
            "examples": [
                "Where is my order",
                "Track my package",
                "When will my order arrive",
                "Shipping status update",
                "My delivery is late",
                "Has my order shipped yet",
                "I need tracking information"
            ],
            "webhook": "/order-status",
            "threshold": 0.78
        },
        "return": {
            "examples": [
                "I want to return this item",
                "How do I get a refund",
                "I need to exchange this product",
                "Send this back for a refund",
                "Return policy question",
                "Money back please",
                "This product is defective, I want a refund"
            ],
            "webhook": "/return-request",
            "threshold": 0.77
        },
        "cancel": {
            "examples": [
                "Cancel my order",
                "I don't want this order anymore",
                "Please stop my order",
                "I changed my mind about my purchase",
                "How do I cancel"
            ],
            "webhook": "/cancel-order",
            "threshold": 0.78
        }
    },
    "healthcare": {
        "escalate": {
            "examples": [
                "I need to speak to a doctor",
                "Connect me to a nurse",
                "This is an emergency",
                "I need urgent help",
                "Let me talk to medical staff"
            ],
            "webhook": "/escalate",
            "threshold": 0.75
        },
        "book_appointment": {
            "examples": [
                "I need to schedule an appointment",
                "Book a visit with the doctor",
                "When is the next available slot",
                "I want to see the doctor",
                "Schedule a consultation",
                "Make an appointment for a checkup",
                "I need to come in for a visit"
            ],
            "webhook": "/book-appointment",
            "threshold": 0.76
        },
        "prescription": {
            "examples": [
                "I need a prescription refill",
                "Can I get my medication renewed",
                "My pills are running out",
                "Refill my prescription please",
                "I need more of my medicine"
            ],
            "webhook": "/prescription",
            "threshold": 0.78
        },
        "results": {
            "examples": [
                "What are my test results",
                "Did my lab work come back",
                "I want to see my medical report",
                "Are my results ready",
                "Blood test results please"
            ],
            "webhook": "/results",
            "threshold": 0.77
        }
    },
    "fintech": {
        "escalate": {
            "examples": [
                "I want to speak to a manager",
                "This is fraud on my account",
                "I need to report unauthorized access",
                "Connect me to security",
                "I want to file a complaint"
            ],
            "webhook": "/escalate",
            "threshold": 0.75
        },
        "balance": {
            "examples": [
                "What's my account balance",
                "How much money do I have",
                "Check my available funds",
                "Show me my balance",
                "What's in my account"
            ],
            "webhook": "/balance",
            "threshold": 0.78
        },
        "transaction": {
            "examples": [
                "Show me my recent transactions",
                "I see a charge I don't recognize",
                "What payments have I made",
                "Transaction history please",
                "I didn't make this payment"
            ],
            "webhook": "/transaction",
            "threshold": 0.77
        },
        "card": {
            "examples": [
                "I lost my card",
                "My card was stolen",
                "Block my card immediately",
                "I need a new card",
                "Freeze my debit card"
            ],
            "webhook": "/card-issue",
            "threshold": 0.78
        }
    },
    "realestate": {
        "escalate": {
            "examples": [
                "I want to speak to an agent",
                "Connect me to a human",
                "I need to talk to someone in person"
            ],
            "webhook": "/escalate",
            "threshold": 0.75
        },
        "book_appointment": {
            "examples": [
                "I want to schedule a viewing",
                "Can I see this property",
                "Book a tour of the house",
                "When can I visit",
                "Schedule a showing please",
                "I want to tour this apartment"
            ],
            "webhook": "/book-appointment",
            "threshold": 0.76
        },
        "pricing": {
            "examples": [
                "What's the price of this property",
                "How much does it cost",
                "Can I afford this house",
                "What are the mortgage options",
                "Price negotiable?"
            ],
            "webhook": "/pricing-inquiry",
            "threshold": 0.77
        },
        "availability": {
            "examples": [
                "Is this property still available",
                "Has this been sold",
                "Is it still on the market",
                "Can I still rent this",
                "Is this listing active"
            ],
            "webhook": "/availability",
            "threshold": 0.78
        }
    },
    "generic": {
        "escalate": {
            "examples": [
                "I want to speak to a manager",
                "Let me talk to a human",
                "Connect me to a real person",
                "I need a supervisor",
                "This isn't helping, I need someone else"
            ],
            "webhook": "/escalate",
            "threshold": 0.75
        },
        "book_appointment": {
            "examples": [
                "I want to schedule a meeting",
                "Book an appointment",
                "When are you available",
                "Can we set up a call",
                "Schedule a consultation",
                "I'd like to book some time"
            ],
            "webhook": "/book-appointment",
            "threshold": 0.76
        },
        "contact_info": {
            "examples": [
                "Here's my phone number",
                "My email is",
                "You can reach me at",
                "Call me back at",
                "Contact me on",
                "I'll give you my details"
            ],
            "webhook": "/ghl-contact",
            "threshold": 0.74
        }
    }
}

# Cache for intent embeddings (computed once per domain)
_intent_embeddings_cache: dict[str, dict] = {}


async def get_embedding(text: str) -> Optional[list[float]]:
    """Get embedding vector for a text string."""
    if not OPENAI_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Embedding API error: {response.status_code}")
                return None

            data = response.json()
            return data["data"][0]["embedding"]

    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None


async def get_embeddings_batch(texts: list[str]) -> Optional[list[list[float]]]:
    """Get embeddings for multiple texts in one API call."""
    if not OPENAI_API_KEY or not texts:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": texts
                },
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Batch embedding API error: {response.status_code}")
                return None

            data = response.json()
            # Sort by index to maintain order
            embeddings = sorted(data["data"], key=lambda x: x["index"])
            return [e["embedding"] for e in embeddings]

    except Exception as e:
        logger.error(f"Batch embedding error: {e}")
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


async def compute_intent_embeddings(domain: str) -> dict:
    """
    Compute and cache embeddings for all intents in a domain.
    Returns dict of intent_name -> {"embedding": avg_embedding, "webhook": str, "threshold": float}
    """
    if domain in _intent_embeddings_cache:
        return _intent_embeddings_cache[domain]

    intents = INTENT_EXAMPLES.get(domain, INTENT_EXAMPLES["generic"])
    result = {}

    for intent_name, config in intents.items():
        examples = config["examples"]
        embeddings = await get_embeddings_batch(examples)

        if embeddings:
            # Average the embeddings for all examples
            avg_embedding = np.mean(embeddings, axis=0).tolist()
            result[intent_name] = {
                "embedding": avg_embedding,
                "webhook": config["webhook"],
                "threshold": config["threshold"]
            }
            logger.info(f"Computed embedding for intent '{intent_name}' ({len(examples)} examples)")
        else:
            logger.warning(f"Failed to compute embedding for intent '{intent_name}'")

    _intent_embeddings_cache[domain] = result
    return result


async def detect_intent_semantic(
    message: str,
    domain: str = None
) -> Optional[tuple[str, float, str]]:
    """
    Detect intent using semantic similarity.

    Returns:
        Tuple of (intent_name, confidence, webhook_url) if intent detected
        None if no intent matches above threshold
    """
    domain = domain or DOMAIN

    # Get or compute intent embeddings
    intent_embeddings = await compute_intent_embeddings(domain)
    if not intent_embeddings:
        logger.warning("No intent embeddings available, falling back to keyword matching")
        return None

    # Get embedding for user message
    message_embedding = await get_embedding(message)
    if not message_embedding:
        return None

    # Find best matching intent
    best_intent = None
    best_score = 0.0
    best_webhook = None

    for intent_name, config in intent_embeddings.items():
        similarity = cosine_similarity(message_embedding, config["embedding"])
        threshold = config["threshold"]

        logger.debug(f"Intent '{intent_name}': similarity={similarity:.3f}, threshold={threshold}")

        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_intent = intent_name
            best_webhook = config["webhook"]

    if best_intent:
        logger.info(f"Semantic intent detected: '{best_intent}' (confidence: {best_score:.3f})")
        return (best_intent, best_score, best_webhook)

    return None


async def detect_intents_hybrid(
    message: str,
    domain: str = None
) -> list[tuple[str, float, str]]:
    """
    Hybrid intent detection: tries semantic first, falls back to keyword matching.

    Returns list of (intent_name, confidence, webhook_url) for all detected intents.
    """
    from .config import get_intent_patterns

    domain = domain or DOMAIN
    detected = []

    # Try semantic detection first
    semantic_result = await detect_intent_semantic(message, domain)
    if semantic_result:
        detected.append(semantic_result)

    # Also check keyword patterns (for intents that might be missed)
    message_lower = message.lower()
    intent_patterns = get_intent_patterns()

    for intent_name, config in intent_patterns.items():
        # Skip if already detected semantically
        if any(d[0] == intent_name for d in detected):
            continue

        if any(keyword in message_lower for keyword in config["keywords"]):
            detected.append((intent_name, 0.5, config["webhook"]))  # 0.5 confidence for keyword match
            logger.info(f"Keyword intent detected: '{intent_name}'")

    return detected
