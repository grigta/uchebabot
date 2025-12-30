-- Migration: Add cost tracking fields
-- Run this on existing SQLite database to add new columns

-- Add total_cost_usd to users table
ALTER TABLE users ADD COLUMN total_cost_usd REAL DEFAULT 0.0;

-- Add aggregated stats and cost to requests table
ALTER TABLE requests ADD COLUMN total_prompt_tokens INTEGER DEFAULT 0;
ALTER TABLE requests ADD COLUMN total_completion_tokens INTEGER DEFAULT 0;
ALTER TABLE requests ADD COLUMN total_all_tokens INTEGER DEFAULT 0;
ALTER TABLE requests ADD COLUMN cost_usd REAL DEFAULT 0.0;
