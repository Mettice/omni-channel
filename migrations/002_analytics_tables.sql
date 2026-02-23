-- Analytics tables for Omni AI
-- Run this in your Supabase SQL editor

-- Message-level analytics
CREATE TABLE IF NOT EXISTS analytics_messages (
  id SERIAL PRIMARY KEY,
  customer_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  role TEXT NOT NULL,
  response_time_ms FLOAT,
  intent TEXT,
  intent_confidence FLOAT,
  domain TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_messages_customer ON analytics_messages(customer_id);
CREATE INDEX IF NOT EXISTS idx_analytics_messages_timestamp ON analytics_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_messages_domain ON analytics_messages(domain);

-- Conversation-level analytics
CREATE TABLE IF NOT EXISTS analytics_conversations (
  id SERIAL PRIMARY KEY,
  customer_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  domain TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  message_count INT DEFAULT 0,
  avg_response_time_ms FLOAT DEFAULT 0,
  intents_detected TEXT,  -- Comma-separated list
  escalated BOOLEAN DEFAULT FALSE,
  resolved BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_analytics_conv_customer ON analytics_conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_analytics_conv_start ON analytics_conversations(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_conv_domain ON analytics_conversations(domain);
CREATE INDEX IF NOT EXISTS idx_analytics_conv_channel ON analytics_conversations(channel);

-- Intent tracking
CREATE TABLE IF NOT EXISTS analytics_intents (
  id SERIAL PRIMARY KEY,
  customer_id TEXT NOT NULL,
  intent TEXT NOT NULL,
  confidence FLOAT NOT NULL,
  webhook_triggered BOOLEAN DEFAULT FALSE,
  domain TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_intents_intent ON analytics_intents(intent);
CREATE INDEX IF NOT EXISTS idx_analytics_intents_timestamp ON analytics_intents(timestamp DESC);

-- Domain configurations (for admin dashboard)
CREATE TABLE IF NOT EXISTS domain_configs (
  id SERIAL PRIMARY KEY,
  domain TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  system_prompt TEXT NOT NULL,
  greeting TEXT NOT NULL,
  primary_color TEXT DEFAULT '#6366f1',
  logo_url TEXT,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default domains
INSERT INTO domain_configs (domain, display_name, system_prompt, greeting) VALUES
('generic', 'Omni AI Demo', 'You are Omni, an AI assistant.', 'Hi! I''m Omni, how can I help?'),
('igaming', 'Gaming Support', 'You are a casino support agent.', 'Welcome to support!'),
('ecommerce', 'E-Commerce Support', 'You are an e-commerce support agent.', 'Hi! How can I help with your order?'),
('healthcare', 'Healthcare Assistant', 'You are a healthcare assistant.', 'Hello, how can I assist you today?'),
('fintech', 'Banking Support', 'You are a banking support agent.', 'Welcome to support!'),
('realestate', 'Real Estate Assistant', 'You are a real estate assistant.', 'Hi! Looking to buy, sell, or rent?')
ON CONFLICT (domain) DO NOTHING;

-- Daily aggregated stats (for faster dashboard loading)
CREATE TABLE IF NOT EXISTS analytics_daily_stats (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  domain TEXT NOT NULL,
  total_conversations INT DEFAULT 0,
  total_messages INT DEFAULT 0,
  avg_response_time_ms FLOAT DEFAULT 0,
  escalation_count INT DEFAULT 0,
  resolution_count INT DEFAULT 0,
  voice_count INT DEFAULT 0,
  chat_count INT DEFAULT 0,
  widget_count INT DEFAULT 0,
  UNIQUE(date, domain)
);

CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON analytics_daily_stats(date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_stats_domain ON analytics_daily_stats(domain);

-- Function to aggregate daily stats (run via cron job)
CREATE OR REPLACE FUNCTION aggregate_daily_stats(target_date DATE DEFAULT CURRENT_DATE - 1)
RETURNS void AS $$
BEGIN
  INSERT INTO analytics_daily_stats (
    date, domain, total_conversations, total_messages,
    avg_response_time_ms, escalation_count, resolution_count,
    voice_count, chat_count, widget_count
  )
  SELECT
    target_date,
    domain,
    COUNT(*) as total_conversations,
    SUM(message_count) as total_messages,
    AVG(avg_response_time_ms) as avg_response_time_ms,
    SUM(CASE WHEN escalated THEN 1 ELSE 0 END) as escalation_count,
    SUM(CASE WHEN resolved THEN 1 ELSE 0 END) as resolution_count,
    SUM(CASE WHEN channel = 'voice' THEN 1 ELSE 0 END) as voice_count,
    SUM(CASE WHEN channel = 'chat' THEN 1 ELSE 0 END) as chat_count,
    SUM(CASE WHEN channel = 'widget' THEN 1 ELSE 0 END) as widget_count
  FROM analytics_conversations
  WHERE DATE(start_time) = target_date
  GROUP BY domain
  ON CONFLICT (date, domain) DO UPDATE SET
    total_conversations = EXCLUDED.total_conversations,
    total_messages = EXCLUDED.total_messages,
    avg_response_time_ms = EXCLUDED.avg_response_time_ms,
    escalation_count = EXCLUDED.escalation_count,
    resolution_count = EXCLUDED.resolution_count,
    voice_count = EXCLUDED.voice_count,
    chat_count = EXCLUDED.chat_count,
    widget_count = EXCLUDED.widget_count;
END;
$$ LANGUAGE plpgsql;
