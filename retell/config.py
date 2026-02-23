"""
Configuration constants and domain settings for Omni AI.
"""
import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('omni')

# === Constants ===
HISTORY_LIMIT = 10
OPENAI_TIMEOUT = 30
WEBHOOK_TIMEOUT = 5
MAX_TOKENS = 150
STREAMING_CHUNK_DELAY = 0.05  # seconds between word chunks

# === Environment Loading ===
def load_dotenv_fallback() -> Optional[str]:
    """Load environment variables from .env file."""
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

# Load env on import
_ENV_PATH = load_dotenv_fallback()
if _ENV_PATH:
    logger.info(f"Loaded environment from: {_ENV_PATH}")

# === API Configuration ===
RETELL_AGENT_ID = os.environ.get("RETELL_AGENT_ID", "agent_f604bb54a90edd0d700a3b40ca")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
RETELL_API_KEY = os.environ.get("RETELL_API_KEY", "")
N8N_WEBHOOK_BASE = os.environ.get("N8N_WEBHOOK_BASE", "")
DOMAIN = os.environ.get("DOMAIN", "generic")

# === Voice Agent Configuration ===
# Map of voice IDs to Retell agent configurations
# To add more voices: create agents in Retell dashboard with different voice_ids
# Then add them here with a friendly name, language, and description
VOICE_AGENTS = {
    "default": {
        "agent_id": RETELL_AGENT_ID,  # agent_f604bb54a90edd0d700a3b40ca
        "name": "Cimo",
        "language": "English",
        "gender": "male",
        "description": "Professional English voice",
        "preview_url": None  # Optional: URL to voice sample
    },
    # Add more voices by creating agents in Retell with different voice_ids:
    # "voice_sarah": {
    #     "agent_id": "agent_xxx",
    #     "name": "Sarah",
    #     "language": "English (US)",
    #     "gender": "female",
    #     "description": "Friendly American female voice"
    # },
    # "voice_spanish": {
    #     "agent_id": "agent_yyy",
    #     "name": "Carlos",
    #     "language": "Spanish",
    #     "gender": "male",
    #     "description": "Native Spanish speaker"
    # },
}

def get_voice_agent(voice_id: str = "default") -> dict:
    """Get agent configuration for a voice ID."""
    return VOICE_AGENTS.get(voice_id, VOICE_AGENTS["default"])

# === Domain-Specific System Prompts ===
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

    "generic": """You are Omni, an AI voice and chat assistant built to demonstrate what AI customer support can do.

IMPORTANT: Keep responses conversational and natural. Avoid using markdown formatting like ** or bullet points. Speak in flowing sentences since this may be read aloud on voice calls.

When someone asks what you can do, explain conversationally:
I handle both voice calls and web chat with shared memory, so customers can switch channels and I remember everything. I can book appointments directly into calendars like Google Calendar or Calendly. I sync contacts to CRMs like GoHighLevel, HubSpot, or Salesforce. I automatically text customers who miss calls. And I work across WhatsApp, Telegram, Instagram, Email, and more. Basically, I'm 24/7 customer support that sounds natural and remembers every conversation.

If they ask about channels or integrations, say something like:
We support voice, web chat, SMS, WhatsApp, Telegram, Instagram, Facebook Messenger, and Email. We can integrate with any CRM or calendar system. What channels or systems do you currently use? We can connect to those.

If they ask about pricing or want to buy:
Say "I can connect you with Dion to discuss pricing and setup for your business. Would you like to share your contact info?" Then collect their name, email, phone, and business name if they agree.

For regular support questions, be helpful and concise. Keep responses under 2-3 sentences when possible.
You remember the full conversation history across all channels - reference past conversations when relevant."""
}

# === Domain-Specific Intent Patterns ===
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
        "book_appointment": {
            "keywords": ["appointment", "schedule", "book", "available", "see doctor", "visit", "consultation", "checkup"],
            "webhook": "/book-appointment"
        },
        "prescription": {
            "keywords": ["prescription", "refill", "medication", "medicine", "pharmacy"],
            "webhook": "/prescription"
        },
        "results": {
            "keywords": ["results", "test results", "lab", "report"],
            "webhook": "/results"
        },
        "contact_info": {
            "keywords": ["call me back", "my number is", "my phone", "contact me", "reach me"],
            "webhook": "/ghl-contact"
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
        "book_appointment": {
            "keywords": ["view", "visit", "see property", "tour", "showing", "schedule", "book", "appointment"],
            "webhook": "/book-appointment"
        },
        "pricing": {
            "keywords": ["price", "cost", "how much", "afford", "mortgage", "financing"],
            "webhook": "/pricing-inquiry"
        },
        "availability": {
            "keywords": ["available", "still available", "sold", "rent", "lease"],
            "webhook": "/availability"
        },
        "contact_info": {
            "keywords": ["call me back", "my number is", "my phone", "my email", "contact me"],
            "webhook": "/ghl-contact"
        }
    },
    "generic": {
        "escalate": {
            "keywords": ["manager", "human", "supervisor", "complaint", "speak to someone", "real person"],
            "webhook": "/escalate"
        },
        "book_appointment": {
            "keywords": ["book", "appointment", "schedule", "available", "calendar", "slot", "meeting", "consultation"],
            "webhook": "/book-appointment"
        },
        "contact_info": {
            "keywords": ["call me back", "my number is", "my email is", "contact me", "reach me"],
            "webhook": "/ghl-contact"
        }
    }
}

# === Domain-Specific Greetings ===
DOMAIN_GREETINGS = {
    "igaming": "Hello! Welcome to support. How can I help you today?",
    "ecommerce": "Hi there! Thanks for calling. How can I help with your order today?",
    "healthcare": "Hello, thank you for calling. How may I assist you with your healthcare needs today?",
    "fintech": "Welcome to support. How can I assist you with your account today?",
    "realestate": "Hi! Thanks for reaching out. Are you looking to buy, sell, or rent today?",
    "generic": "Hi! I'm Omni, an AI assistant that handles voice and chat support. Feel free to test me out, or ask what I can do for your business!"
}


def get_system_prompt(customer_id: str = "", context: str = "") -> str:
    """Get the system prompt for the current domain."""
    base_prompt = SYSTEM_PROMPTS.get(DOMAIN, SYSTEM_PROMPTS["generic"])
    if context:
        return f"{base_prompt}\n\nCustomer history:\n{context}"
    return base_prompt


def get_intent_patterns() -> dict:
    """Get intent patterns for the current domain."""
    return DOMAIN_INTENTS.get(DOMAIN, DOMAIN_INTENTS["generic"])


def get_greeting() -> str:
    """Get the greeting for the current domain."""
    return DOMAIN_GREETINGS.get(DOMAIN, DOMAIN_GREETINGS["generic"])
