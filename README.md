# Omni AI - Multi-Channel Customer Support Platform

A production-ready AI customer support platform that combines voice calls, web chat, and workflow automation with shared memory across all channels.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     OMNI AI ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FRONTEND (index.html)                                          │
│  ├── Chat UI (vanilla JS + CSS)                                 │
│  ├── Voice UI (Retell Web SDK)                                  │
│  └── Session persistence (localStorage)                         │
│                                                                 │
│         ↓ HTTP/WebSocket                                        │
│                                                                 │
│  BACKEND (retell/server.py - aiohttp)                           │
│  ├── POST /create-call → Retell API                             │
│  ├── POST /chat → OpenAI + Supabase                             │
│  ├── WS /llm-websocket/{call_id} → Retell streaming             │
│  ├── Intent detection → n8n webhooks                            │
│  └── Domain-specific prompts & behaviors                        │
│                                                                 │
│         ↓ External APIs                                         │
│                                                                 │
│  ├── OpenAI (GPT-4o) - Response generation                      │
│  ├── Retell AI - Voice call handling                            │
│  ├── Supabase - Conversation history (PostgreSQL)               │
│  └── n8n - Workflow automation                                  │
│      ├── GoHighLevel (CRM)                                      │
│      ├── Google Calendar                                        │
│      ├── Twilio (SMS)                                           │
│      └── Custom webhooks                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
omni n8n/
├── retell/                    # Backend Python package
│   ├── __init__.py            # Package initialization
│   ├── server.py              # Main HTTP/WebSocket handlers
│   ├── config.py              # Configuration & domain settings
│   ├── db.py                  # Supabase database operations
│   ├── llm.py                 # OpenAI LLM operations
│   ├── intents.py             # Intent detection & webhooks
│   ├── embeddings.py          # Semantic intent detection (NEW)
│   ├── summarization.py       # Conversation summarization (NEW)
│   └── analytics.py           # Metrics tracking (NEW)
├── migrations/                # Database migrations
│   ├── 001_initial_schema.sql # Initial Supabase schema
│   └── 002_analytics_tables.sql # Analytics tables (NEW)
├── n8n-workflows/             # Workflow automation templates
│   ├── ghl-integration.json   # GoHighLevel CRM sync
│   ├── calendar-booking.json  # Calendar & appointment booking
│   ├── escalation-workflow.json # Escalation to humans
│   ├── twilio-sms.json        # SMS notifications
│   ├── lead-gen-pipeline.json # Automated lead generation
│   └── bonus-status-workflow.json # iGaming bonus lookup
├── run.py                     # Server entry point
├── index.html                 # Full-page chat/voice app
├── landing.html               # Sales landing page
├── admin.html                 # Admin dashboard (NEW)
├── widget.js                  # Embeddable chat widget
├── widget-demo.html           # Widget embedding demo
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (secrets)
├── ngrok.yml                  # ngrok tunnel configuration
└── client-config-template.env # Multi-tenant config template
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | Python + aiohttp | Async web framework |
| **AI/LLM** | OpenAI GPT-4o | Response generation |
| **Voice** | Retell AI | Voice call handling & TTS |
| **Database** | Supabase (PostgreSQL) | Conversation persistence |
| **HTTP Client** | httpx | Async webhook requests |
| **Frontend** | Vanilla HTML/CSS/JS | Chat UI |
| **Voice SDK** | Retell Web Client | Browser voice calls |
| **Workflows** | n8n | Automation & integrations |
| **Hosting** | Railway (backend), Vercel (frontend) | Production deployment |

## Core Features

### 1. Multi-Channel Support
- **Voice Calls**: Real-time voice conversations via Retell AI
- **Web Chat**: Text-based chat with markdown support
- **Shared Memory**: Same conversation history across all channels

### 2. Multi-Domain Architecture
Supports 6 industry configurations out of the box:

| Domain | Use Case | Example Intents |
|--------|----------|-----------------|
| `igaming` | Casino/gaming support | withdrawal, bonus, verification |
| `ecommerce` | E-commerce shops | order_status, return, cancel |
| `healthcare` | Medical practices | book_appointment, prescription |
| `fintech` | Banking/finance | balance, transaction, card |
| `realestate` | Real estate agents | book_appointment, pricing |
| `generic` | Demo/versatile | book_appointment, contact_info |

### 3. Semantic Intent Detection (NEW)
- **Hybrid detection**: Embeddings + keyword fallback
- Uses OpenAI text-embedding-3-small for semantic matching
- Configurable confidence thresholds per intent
- More robust than keyword-only matching

### 4. Conversation Summarization (NEW)
- Auto-summarizes long conversations (20+ messages)
- Preserves recent messages while condensing history
- Stays within context limits automatically
- Uses gpt-4o-mini for efficient summarization

### 5. Analytics & Metrics (NEW)
- Track conversations, messages, response times
- Intent detection analytics
- Channel distribution metrics
- Escalation and resolution rates
- Real-time dashboard

### 6. Admin Dashboard (NEW)
- View analytics and metrics
- Manage domain configurations
- Update prompts and greetings without code changes
- Create new domains on the fly

### 7. Streaming Responses
- Voice: Token-by-token streaming for natural speech
- Chat: Full response delivery

## Data Flow

### Voice Call Flow
```
1. User clicks "Call" → Request microphone permission
2. Frontend POST /create-call?customer_id={id}
3. Backend calls Retell API → Returns access_token
4. Frontend initializes Retell WebClient
5. Retell establishes WebSocket to /llm-websocket/{call_id}
6. Backend extracts metadata → Loads conversation history
7. User speaks → Retell transcribes audio
8. Backend receives response_required event
9. Backend calls OpenAI GPT-4o with system prompt + history
10. Backend streams tokens back to Retell
11. Retell converts to speech → Plays audio
12. Backend saves response to Supabase
13. Intent detection triggers n8n webhooks (async)
```

### Web Chat Flow
```
1. User types message in chat input
2. Frontend POST /chat with {player_id, message}
3. Backend saves user message to Supabase
4. Backend loads chat history
5. Backend calls OpenAI with system prompt + history
6. Backend returns JSON response
7. Frontend displays with markdown formatting
8. Backend saves agent response to Supabase
9. Intent detection triggers n8n webhooks (background)
```

## API Endpoints

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/create-call` | POST | Create Retell voice call |
| `/chat` | POST | Send chat message |
| `/llm-websocket/{call_id}` | WS | Live voice call handler |

### Analytics API (NEW)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/analytics/stats` | GET | Get dashboard statistics |
| `/api/analytics/conversations` | GET | List recent conversations |

### Domain Management API (NEW)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/domains` | GET | List all domain configs |
| `/api/domains` | POST | Create new domain |
| `/api/domains` | PUT | Update domain config |

## Getting Started

### Prerequisites
- Python 3.10+
- API keys for: OpenAI, Retell AI, Supabase

### 1. Clone & Setup Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create `.env` in the project root:

```env
OPENAI_API_KEY=sk-...
RETELL_API_KEY=key_...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ...
DOMAIN=generic
N8N_WEBHOOK_BASE=https://your-n8n.com/webhook  # Optional
```

### 4. Database Setup (Supabase)

Run the migration in your Supabase SQL editor (`migrations/001_initial_schema.sql`):

```sql
-- Conversation history
CREATE TABLE IF NOT EXISTS player_sessions (
  id SERIAL PRIMARY KEY,
  player_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  role TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_player_sessions_player_id ON player_sessions(player_id);
CREATE INDEX IF NOT EXISTS idx_player_sessions_created_at ON player_sessions(created_at DESC);

-- Call ID to Customer ID mapping (for multi-instance support)
CREATE TABLE IF NOT EXISTS call_mappings (
  call_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_mappings_created_at ON call_mappings(created_at);
```

### 5. Run the Backend

```bash
python run.py
```

Server starts on `http://localhost:8080`

**Endpoints:**
- `GET /health` - Health check for monitoring
- `POST /create-call` - Create voice call
- `POST /chat` - Send chat message
- `WS /llm-websocket/{call_id}` - Voice WebSocket

### 6. Run the Frontend

```bash
python -m http.server 3000
```

Open `http://localhost:3000/index.html`

## Deployment

### Backend (Railway)

1. Push to GitHub
2. Create Railway project from repo
3. Set environment variables:
   - `OPENAI_API_KEY`
   - `RETELL_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `DOMAIN`
   - `RETELL_AGENT_ID` (optional, has default)
4. Start command: `python run.py`

### Frontend (Vercel)

1. Update `index.html` URLs to production backend:
```javascript
const WEBHOOK_URL = 'https://your-railway-app.up.railway.app/chat';
const VOICE_URL = 'https://your-railway-app.up.railway.app';
```
2. Deploy as static site to Vercel

### Local Development with ngrok

```bash
ngrok start --all --config ngrok.yml
```

This exposes:
- `localhost:8080` → Backend (for Retell webhooks)
- `localhost:5678` → n8n (for workflow testing)

## n8n Workflow Templates

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `ghl-integration.json` | Sync contacts to GoHighLevel CRM | contact_info intent |
| `calendar-booking.json` | Book appointments via Google Calendar | book_appointment intent |
| `escalation-workflow.json` | Route to human agents | escalate intent |
| `twilio-sms.json` | Send SMS notifications | Various events |
| `lead-gen-pipeline.json` | Automated B2B lead scraping | Scheduled daily |
| `bonus-status-workflow.json` | Look up player bonuses (iGaming) | bonus intent |

## Key Code Components

### Module Structure

```
retell/
├── config.py      # Configuration & domain settings
│   ├── SYSTEM_PROMPTS      # System prompts per domain
│   ├── DOMAIN_INTENTS      # Intent patterns per domain
│   ├── DOMAIN_GREETINGS    # Greetings per domain
│   ├── get_system_prompt() # Get prompt for current domain
│   ├── get_intent_patterns()# Get intents for current domain
│   └── get_greeting()      # Get greeting for current domain
│
├── db.py          # Database operations
│   ├── get_customer_messages() # Load chat history
│   ├── save_message()          # Persist message
│   ├── store_call_mapping()    # Store call→customer mapping
│   ├── get_call_mapping()      # Retrieve customer for call
│   └── delete_call_mapping()   # Cleanup after call ends
│
├── llm.py         # OpenAI operations
│   ├── generate_response()          # Non-streaming (chat)
│   └── generate_response_streaming()# Streaming (voice)
│
├── intents.py     # Intent detection
│   └── detect_and_trigger_intents() # Match keywords → webhook
│
└── server.py      # HTTP/WebSocket handlers
    ├── health()       # GET /health
    ├── create_call()  # POST /create-call
    ├── chat()         # POST /chat
    ├── llm_websocket()# WS /llm-websocket/{call_id}
    ├── check_rate_limit()    # Rate limiting
    ├── validate_customer_id()# Input validation
    └── sanitize_message()    # XSS prevention
```

## Configuration

### Adding a New Domain

1. Add system prompt to `SYSTEM_PROMPTS` dict
2. Add intent patterns to `DOMAIN_INTENTS` dict
3. Add greeting to `DOMAIN_GREETINGS` dict
4. Set `DOMAIN=your_domain` in environment

### Customizing Intent Detection

Edit `DOMAIN_INTENTS` in `server.py`:

```python
"your_domain": {
    "intent_name": {
        "keywords": ["keyword1", "keyword2"],
        "webhook": "/your-webhook-endpoint"
    }
}
```

## Production Considerations

### Security (Implemented)
- Store all API keys in environment variables
- Never commit `.env` to version control
- Use HTTPS in production
- Rate limiting on `/chat` and `/create-call` (30 req/min per IP)
- Input validation and sanitization
- XSS prevention in frontend

### Scalability
- Call mappings stored in Supabase (multi-instance ready)
- Shared HTTP client with connection pooling
- For high traffic: Replace in-memory rate limiter with Redis
- Consider async task queues for n8n webhooks

### Monitoring (Implemented)
- Structured logging with timestamps
- Health check endpoint: `GET /health`
- Track API latencies and error rates

## Admin Dashboard

Access the admin dashboard at `admin.html`:

```bash
python -m http.server 3000
# Open http://localhost:3000/admin.html
```

**Features:**
- **Dashboard**: View conversation metrics, channel distribution, top intents
- **Conversations**: Browse and filter conversation history
- **Domains**: Manage domain configurations without code changes
- **Settings**: Configure API endpoint

**Database Setup:**
Run the analytics migrations before using the dashboard:

```sql
-- Run migrations/002_analytics_tables.sql in Supabase
```

## Sales & Embedding

### Landing Page

Sales-ready landing page at `landing.html`:
- Hero section with live demo embed
- Features, integrations, pricing sections
- Mobile responsive
- Ready to customize

```bash
# Preview locally
python -m http.server 3000
# Open http://localhost:3000/landing.html
```

### Embeddable Widget

Drop-in chat widget for any website (`widget.js`):

```html
<!-- Add before </body> -->
<script src="https://your-domain.com/widget.js"></script>
```

**Customization options:**

```html
<script src="https://your-domain.com/widget.js"
  data-api="https://your-api.com"
  data-position="right"
  data-color="#6366f1"
  data-title="Support"
  data-greeting="Hi! How can I help?"
></script>
```

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-api` | Omni API | Backend API URL |
| `data-position` | `right` | `left` or `right` |
| `data-color` | `#6366f1` | Primary color (hex) |
| `data-title` | `Omni AI` | Header title |
| `data-greeting` | `Hi! How can I help you today?` | Initial message |

See `widget-demo.html` for a live example.

## License

MIT
