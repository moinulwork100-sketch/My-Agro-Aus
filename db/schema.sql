-- MyAgro Database Schema
-- Run this in the Supabase SQL editor before seed.sql.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Farmers
CREATE TABLE IF NOT EXISTS farmers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT,
  verified BOOLEAN DEFAULT FALSE,
  rating NUMERIC(3,1) DEFAULT 0,
  completed_projects INT DEFAULT 0,
  on_time_rate INT DEFAULT 0,
  years_experience INT DEFAULT 1,
  failed_projects INT DEFAULT 0,
  risk_classification TEXT,
  bio TEXT,
  portrait_url TEXT,
  farm_name TEXT,
  farm_location TEXT,
  farm_size TEXT,
  crop_categories TEXT[] DEFAULT '{}',
  land_ownership_verification TEXT DEFAULT 'not_started',
  government_id_verification TEXT DEFAULT 'not_started',
  farm_inspection_verification TEXT DEFAULT 'not_started',
  banking_verification TEXT DEFAULT 'not_started',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE farmers ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS years_experience INT DEFAULT 1;
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS failed_projects INT DEFAULT 0;
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS farm_name TEXT;
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS farm_location TEXT;
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS farm_size TEXT;
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS crop_categories TEXT[] DEFAULT '{}';
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS land_ownership_verification TEXT DEFAULT 'not_started';
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS government_id_verification TEXT DEFAULT 'not_started';
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS farm_inspection_verification TEXT DEFAULT 'not_started';
ALTER TABLE farmers ADD COLUMN IF NOT EXISTS banking_verification TEXT DEFAULT 'not_started';
CREATE UNIQUE INDEX IF NOT EXISTS farmers_email_idx ON farmers(email) WHERE email IS NOT NULL;

-- Users. Passwords are stored as salted PBKDF2 hashes.
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  phone TEXT,
  location TEXT,
  country TEXT,
  password_hash TEXT,
  role TEXT NOT NULL DEFAULT 'investor' CHECK (role IN ('investor', 'farmer', 'admin')),
  farmer_id UUID REFERENCES farmers(id),
  email_verified BOOLEAN DEFAULT FALSE,
  email_verified_at TIMESTAMPTZ,
  profile_completion INT DEFAULT 0,
  investor_type TEXT CHECK (investor_type IS NULL OR investor_type IN ('Individual', 'Company')),
  investment_interests TEXT[] DEFAULT '{}',
  risk_tolerance TEXT CHECK (risk_tolerance IS NULL OR risk_tolerance IN ('Low', 'Medium', 'High')),
  preferred_crops TEXT[] DEFAULT '{}',
  preferred_investment_size TEXT,
  profile_photo_url TEXT,
  kyc_status TEXT DEFAULT 'not_started',
  government_id_verification TEXT DEFAULT 'not_started',
  bank_verification TEXT DEFAULT 'not_started',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'investor';
ALTER TABLE users ADD COLUMN IF NOT EXISTS farmer_id UUID REFERENCES farmers(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS country TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_completion INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS investor_type TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS investment_interests TEXT[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS risk_tolerance TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_crops TEXT[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_investment_size TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_photo_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status TEXT DEFAULT 'not_started';
ALTER TABLE users ADD COLUMN IF NOT EXISTS government_id_verification TEXT DEFAULT 'not_started';
ALTER TABLE users ADD COLUMN IF NOT EXISTS bank_verification TEXT DEFAULT 'not_started';

-- Password reset tokens are stored hashed and expire after use/time.
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS password_reset_tokens_hash_idx ON password_reset_tokens(token_hash);

-- Email verification tokens are stored hashed and expire after use/time.
CREATE TABLE IF NOT EXISTS email_verification_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS email_verification_tokens_hash_idx ON email_verification_tokens(token_hash);

-- Farms
CREATE TABLE IF NOT EXISTS farms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id UUID REFERENCES farmers(id),
  name TEXT NOT NULL,
  crop_type TEXT NOT NULL,
  location TEXT NOT NULL,
  expected_roi NUMERIC(5,2) NOT NULL,
  risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MODERATE', 'MEDIUM', 'HIGH')),
  risk_score INT,
  risk_reasoning_summary TEXT,
  ai_insight TEXT,
  success_rate INT,
  duration_months INT,
  harvest_date DATE,
  status TEXT DEFAULT 'active',
  funded_percent INT DEFAULT 0,
  total_funding_goal NUMERIC(12,2),
  days_left INT,
  image_type TEXT DEFAULT 'corn',
  current_milestone TEXT DEFAULT 'Planning',
  progress_percent INT DEFAULT 0,
  expected_completion_date DATE,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE farms DROP CONSTRAINT IF EXISTS farms_risk_level_check;
ALTER TABLE farms ADD CONSTRAINT farms_risk_level_check CHECK (risk_level IN ('LOW', 'MODERATE', 'MEDIUM', 'HIGH'));
ALTER TABLE farms ADD COLUMN IF NOT EXISTS risk_score INT;
ALTER TABLE farms ADD COLUMN IF NOT EXISTS risk_reasoning_summary TEXT;
ALTER TABLE farms ADD COLUMN IF NOT EXISTS ai_insight TEXT;
ALTER TABLE farms ADD COLUMN IF NOT EXISTS current_milestone TEXT DEFAULT 'Planning';
ALTER TABLE farms ADD COLUMN IF NOT EXISTS progress_percent INT DEFAULT 0;
ALTER TABLE farms ADD COLUMN IF NOT EXISTS expected_completion_date DATE;

-- Investments
CREATE TABLE IF NOT EXISTS investments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  farm_id UUID REFERENCES farms(id),
  amount NUMERIC(12,2) NOT NULL,
  expected_return NUMERIC(12,2),
  gross_profit NUMERIC(12,2) DEFAULT 0,
  investor_fee_rate NUMERIC(5,4) DEFAULT 0,
  investor_platform_fee NUMERIC(12,2) DEFAULT 0,
  net_profit NUMERIC(12,2) DEFAULT 0,
  farmer_fee_rate NUMERIC(5,4) DEFAULT 0,
  farmer_platform_fee NUMERIC(12,2) DEFAULT 0,
  farmer_payout NUMERIC(12,2) DEFAULT 0,
  loss_protection_applied BOOLEAN DEFAULT FALSE,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE investments ADD COLUMN IF NOT EXISTS gross_profit NUMERIC(12,2) DEFAULT 0;
ALTER TABLE investments ADD COLUMN IF NOT EXISTS investor_fee_rate NUMERIC(5,4) DEFAULT 0;
ALTER TABLE investments ADD COLUMN IF NOT EXISTS investor_platform_fee NUMERIC(12,2) DEFAULT 0;
ALTER TABLE investments ADD COLUMN IF NOT EXISTS net_profit NUMERIC(12,2) DEFAULT 0;
ALTER TABLE investments ADD COLUMN IF NOT EXISTS farmer_fee_rate NUMERIC(5,4) DEFAULT 0;
ALTER TABLE investments ADD COLUMN IF NOT EXISTS farmer_platform_fee NUMERIC(12,2) DEFAULT 0;
ALTER TABLE investments ADD COLUMN IF NOT EXISTS farmer_payout NUMERIC(12,2) DEFAULT 0;
ALTER TABLE investments ADD COLUMN IF NOT EXISTS loss_protection_applied BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS investments_user_id_idx ON investments(user_id);
CREATE INDEX IF NOT EXISTS investments_farm_id_idx ON investments(farm_id);

-- Configurable platform fee rules managed through the admin API.
CREATE TABLE IF NOT EXISTS platform_fee_rules (
  id TEXT PRIMARY KEY,
  audience TEXT NOT NULL CHECK (audience IN ('investor', 'farmer')),
  label TEXT NOT NULL,
  rate NUMERIC(5,4) NOT NULL CHECK (rate BETWEEN 0 AND 1),
  minimum NUMERIC(12,2),
  maximum NUMERIC(12,2),
  sort_order INT DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Farm progress updates
CREATE TABLE IF NOT EXISTS progress_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id UUID REFERENCES farms(id),
  milestone TEXT DEFAULT 'Planning',
  progress_percent INT DEFAULT 0,
  stage TEXT,
  health TEXT,
  weather TEXT,
  photo_url TEXT,
  video_url TEXT,
  document_url TEXT,
  yield_report TEXT,
  expense_report TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS milestone TEXT DEFAULT 'Planning';
ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS progress_percent INT DEFAULT 0;
ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS video_url TEXT;
ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS document_url TEXT;
ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS yield_report TEXT;
ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS expense_report TEXT;

-- Investor-farmer messages
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  investment_id UUID REFERENCES investments(id),
  sender TEXT NOT NULL CHECK (sender IN ('investor', 'farmer')),
  body TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Farmer reviews
CREATE TABLE IF NOT EXISTS reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  farmer_id UUID REFERENCES farmers(id),
  user_id UUID REFERENCES users(id),
  rating INT CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  reviewer_name TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Direct browser access to Supabase tables is locked down.
-- The FastAPI backend uses the service role key server-side and performs role checks.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_verification_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE farmers ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_fee_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE progress_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
