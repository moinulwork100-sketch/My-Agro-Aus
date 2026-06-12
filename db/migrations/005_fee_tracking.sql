-- Migration 005: fee_settlements and fee_notifications tables
-- Apply in the Supabase SQL editor.

CREATE TABLE IF NOT EXISTS fee_settlements (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  investment_id UUID NOT NULL REFERENCES investments(id),
  user_id       UUID NOT NULL REFERENCES users(id),
  fee_type      TEXT NOT NULL CHECK (fee_type IN ('investor', 'farmer')),
  amount        NUMERIC(12,2) NOT NULL,
  settled_at    TIMESTAMPTZ DEFAULT now(),
  settled_by    UUID REFERENCES users(id),
  notes         TEXT
);
CREATE INDEX IF NOT EXISTS fee_settlements_inv_idx  ON fee_settlements(investment_id);
CREATE INDEX IF NOT EXISTS fee_settlements_user_idx ON fee_settlements(user_id);

CREATE TABLE IF NOT EXISTS fee_notifications (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id),
  admin_id   UUID NOT NULL REFERENCES users(id),
  message    TEXT NOT NULL,
  read_at    TIMESTAMPTZ,
  sent_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS fee_notifications_user_idx ON fee_notifications(user_id);

ALTER TABLE fee_settlements   ENABLE ROW LEVEL SECURITY;
ALTER TABLE fee_notifications ENABLE ROW LEVEL SECURITY;
