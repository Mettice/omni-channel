-- Omni AI Database Schema
-- Run this in your Supabase SQL editor

-- Player/Customer sessions table (conversation history)
CREATE TABLE IF NOT EXISTS player_sessions (
  id SERIAL PRIMARY KEY,
  player_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  role TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_player_sessions_player_id ON player_sessions(player_id);
CREATE INDEX IF NOT EXISTS idx_player_sessions_created_at ON player_sessions(created_at DESC);

-- Call mappings table (for persistent call_id -> customer_id mapping)
-- This replaces the in-memory CALL_CUSTOMER_MAP for multi-instance support
CREATE TABLE IF NOT EXISTS call_mappings (
  call_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for cleanup of old mappings
CREATE INDEX IF NOT EXISTS idx_call_mappings_created_at ON call_mappings(created_at);

-- Optional: Auto-cleanup old call mappings (calls older than 24 hours)
-- Run this as a scheduled job or enable the pg_cron extension
-- DELETE FROM call_mappings WHERE created_at < NOW() - INTERVAL '24 hours';
