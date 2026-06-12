-- MyAgro Seed Data
-- Run this after schema.sql in the Supabase SQL editor.

-- Farmers
INSERT INTO farmers (id, name, email, verified, rating, completed_projects, on_time_rate, years_experience, failed_projects, risk_classification, bio, portrait_url, farm_name, farm_location, farm_size, crop_categories, land_ownership_verification, government_id_verification, farm_inspection_verification, banking_verification) VALUES
  ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Jack Row', 'jack@myagro.test', true, 4.8, 14, 92, 15, 0, 'LOW',
   'Jack Row is an experienced corn and wheat farmer with over 15 years of farming in Victoria. Known for consistent returns and transparent communication with investors.',
   'https://randomuser.me/api/portraits/men/32.jpg', 'Row Family Grains', 'Victoria', '120 hectares', ARRAY['Corn', 'Wheat'], 'verified', 'verified', 'verified', 'verified'),
  ('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'John Spay', 'john@myagro.test', true, 4.6, 8, 88, 9, 0, 'MEDIUM',
   'John Spay specialises in organic rice cultivation across New South Wales. Certified organic producer since 2019.',
   'https://randomuser.me/api/portraits/men/45.jpg', 'Spay Organic Rice', 'New South Wales', '80 hectares', ARRAY['Organic Rice'], 'verified', 'verified', 'verified', 'verified'),
  ('c3d4e5f6-a7b8-9012-cdef-123456789012', 'Maria Chen', 'maria@myagro.test', true, 4.9, 21, 95, 18, 0, 'LOW',
   'Maria Chen runs a diversified livestock operation in Queensland with reliable processor contracts and 21 completed cycles.',
   'https://randomuser.me/api/portraits/women/28.jpg', 'Chen Livestock Cooperative', 'Queensland', '220 hectares', ARRAY['Livestock'], 'verified', 'verified', 'verified', 'verified'),
  ('d4e5f6a7-b8c9-0123-def0-234567890123', 'Robert Walsh', 'robert@myagro.test', false, 4.2, 3, 80, 6, 1, 'HIGH',
   'Robert Walsh is expanding his potato farming operation in South Australia with higher risk and higher reward potential.',
   'https://randomuser.me/api/portraits/men/67.jpg', 'Walsh Potato Expansion', 'South Australia', '45 hectares', ARRAY['Potato'], 'pending', 'pending', 'pending', 'pending')
ON CONFLICT (id) DO UPDATE SET
  email = EXCLUDED.email,
  verified = EXCLUDED.verified,
  rating = EXCLUDED.rating,
  completed_projects = EXCLUDED.completed_projects,
  on_time_rate = EXCLUDED.on_time_rate,
  years_experience = EXCLUDED.years_experience,
  failed_projects = EXCLUDED.failed_projects,
  risk_classification = EXCLUDED.risk_classification,
  bio = EXCLUDED.bio,
  portrait_url = EXCLUDED.portrait_url,
  farm_name = EXCLUDED.farm_name,
  farm_location = EXCLUDED.farm_location,
  farm_size = EXCLUDED.farm_size,
  crop_categories = EXCLUDED.crop_categories,
  land_ownership_verification = EXCLUDED.land_ownership_verification,
  government_id_verification = EXCLUDED.government_id_verification,
  farm_inspection_verification = EXCLUDED.farm_inspection_verification,
  banking_verification = EXCLUDED.banking_verification;

-- App users by role. Demo passwords use the email address through the legacy dev fallback.
INSERT INTO users (id, name, email, phone, location, country, role, farmer_id, email_verified, profile_completion, investor_type, investment_interests, risk_tolerance, preferred_crops, preferred_investment_size, kyc_status, government_id_verification, bank_verification) VALUES
  ('11111111-1111-4111-8111-111111111111', 'Ava Investor', 'ava@myagro.test', '0400 111 111', 'Melbourne', 'Australia', 'investor', NULL, true, 100, 'Individual', ARRAY['High-yield crops', 'Short-cycle farms'], 'Medium', ARRAY['Corn', 'Organic Rice'], '$500 - $2,500', 'pending', 'not_started', 'not_started'),
  ('22222222-2222-4222-8222-222222222222', 'Noah Investor', 'noah@myagro.test', '0400 222 222', 'Sydney', 'Australia', 'investor', NULL, true, 100, 'Individual', ARRAY['Livestock', 'Diversified farms'], 'Low', ARRAY['Livestock', 'Corn'], '$1,000 - $5,000', 'pending', 'not_started', 'not_started'),
  ('33333333-3333-4333-8333-333333333333', 'Jack Row', 'jack@myagro.test', '0400 333 333', 'Victoria', 'Australia', 'farmer', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', true, 100, NULL, '{}', NULL, '{}', NULL, 'not_started', 'verified', 'verified'),
  ('44444444-4444-4444-8444-444444444444', 'John Spay', 'john@myagro.test', '0400 444 444', 'New South Wales', 'Australia', 'farmer', 'b2c3d4e5-f6a7-8901-bcde-f12345678901', true, 100, NULL, '{}', NULL, '{}', NULL, 'not_started', 'verified', 'verified'),
  ('99999999-9999-4999-8999-999999999999', 'MyAgro Admin', 'admin@myagro.test', NULL, 'Platform HQ', 'Australia', 'admin', NULL, true, 100, NULL, '{}', NULL, '{}', NULL, 'not_started', 'verified', 'verified'),
  ('55555555-5555-4555-8555-555555555555', 'Maria Chen', 'maria@myagro.test', '0400 555 555', 'Queensland', 'Australia', 'farmer', 'c3d4e5f6-a7b8-9012-cdef-123456789012', true, 100, NULL, '{}', NULL, '{}', NULL, 'not_started', 'verified', 'verified')
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  email = EXCLUDED.email,
  phone = EXCLUDED.phone,
  location = EXCLUDED.location,
  country = EXCLUDED.country,
  role = EXCLUDED.role,
  farmer_id = EXCLUDED.farmer_id,
  email_verified = EXCLUDED.email_verified,
  profile_completion = EXCLUDED.profile_completion,
  investor_type = EXCLUDED.investor_type,
  investment_interests = EXCLUDED.investment_interests,
  risk_tolerance = EXCLUDED.risk_tolerance,
  preferred_crops = EXCLUDED.preferred_crops,
  preferred_investment_size = EXCLUDED.preferred_investment_size,
  kyc_status = EXCLUDED.kyc_status,
  government_id_verification = EXCLUDED.government_id_verification,
  bank_verification = EXCLUDED.bank_verification;

-- Farms
INSERT INTO farms (id, farmer_id, name, crop_type, location, expected_roi, risk_level, risk_score, risk_reasoning_summary, ai_insight, success_rate, duration_months, harvest_date, status, funded_percent, total_funding_goal, days_left, image_type, current_milestone, progress_percent, expected_completion_date) VALUES
  ('f1a2b3c4-d5e6-7890-abcd-ef1234567890', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
   'Jack Row Corn Project', 'Corn', 'Victoria', 11.0, 'LOW', 84,
   'LOW RISK (84/100): strong farmer reputation, 92% success rate, and no failed projects.',
   'Jack Row has completed 14 projects with a 92% success rate and maintains a 4.8-star investor rating. This project is considered LOW RISK.',
   92, 6, '2026-10-01', 'active', 70, 500000, 45, 'corn', 'Growing', 55, '2026-10-01'),
  ('f2b3c4d5-e6f7-8901-bcde-f12345678901', 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
   'John Spay Organic Rice', 'Organic Rice', 'New South Wales', 14.5, 'MEDIUM', 71,
   'MEDIUM RISK (71/100): good history offset by crop and funding execution risk.',
   'John Spay has completed 8 projects with an 85% success rate and maintains a 4.6-star investor rating. This project is considered MEDIUM RISK.',
   85, 8, '2026-12-01', 'active', 55, 350000, 60, 'rice', 'Planting', 35, '2026-12-01'),
  ('f3c4d5e6-f7a8-9012-cdef-123456789012', 'c3d4e5f6-a7b8-9012-cdef-123456789012',
   'Maria Chen Livestock Fund', 'Livestock', 'Queensland', 9.5, 'LOW', 91,
   'LOW RISK (91/100): excellent completion record, high satisfaction, and full funding.',
   'Maria Chen has completed 21 projects with a 97% success rate and maintains a 4.9-star investor rating. This project is considered LOW RISK.',
   97, 12, '2027-03-01', 'completed', 100, 800000, 0, 'livestock', 'Completed', 100, '2027-03-01'),
  ('f4d5e6f7-a8b9-0123-def0-234567890123', 'd4e5f6a7-b8c9-0123-def0-234567890123',
   'Walsh Potato Expansion', 'Potato', 'South Australia', 18.0, 'HIGH', 48,
   'HIGH RISK (48/100): limited project history, unverified farmer profile, and a recorded failed project.',
   'Robert Walsh has completed 3 projects with a 72% success rate and maintains a 4.2-star investor rating. This project is considered HIGH RISK.',
   72, 5, '2026-09-01', 'active', 35, 200000, 30, 'potato', 'Land Preparation', 20, '2026-09-01')
ON CONFLICT (id) DO UPDATE SET
  farmer_id = EXCLUDED.farmer_id,
  name = EXCLUDED.name,
  crop_type = EXCLUDED.crop_type,
  location = EXCLUDED.location,
  expected_roi = EXCLUDED.expected_roi,
  risk_level = EXCLUDED.risk_level,
  risk_score = EXCLUDED.risk_score,
  risk_reasoning_summary = EXCLUDED.risk_reasoning_summary,
  ai_insight = EXCLUDED.ai_insight,
  success_rate = EXCLUDED.success_rate,
  duration_months = EXCLUDED.duration_months,
  harvest_date = EXCLUDED.harvest_date,
  status = EXCLUDED.status,
  funded_percent = EXCLUDED.funded_percent,
  total_funding_goal = EXCLUDED.total_funding_goal,
  days_left = EXCLUDED.days_left,
  image_type = EXCLUDED.image_type,
  current_milestone = EXCLUDED.current_milestone,
  progress_percent = EXCLUDED.progress_percent,
  expected_completion_date = EXCLUDED.expected_completion_date;

-- Demo investments. Fee defaults use ROI-based investor tiers and funding-volume farmer tiers.
INSERT INTO investments (id, user_id, farm_id, amount, expected_return, gross_profit, investor_fee_rate, investor_platform_fee, net_profit, farmer_fee_rate, farmer_platform_fee, farmer_payout, loss_protection_applied, status, created_at) VALUES
  ('81111111-1111-4111-8111-111111111111', '11111111-1111-4111-8111-111111111111', 'f1a2b3c4-d5e6-7890-abcd-ef1234567890',
   1000, 1110, 110, 0.15, 16.50, 93.50, 0.15, 16.50, 983.50, false, 'active', now() - interval '2 months'),
  ('82222222-2222-4222-8222-222222222222', '11111111-1111-4111-8111-111111111111', 'f2b3c4d5-e6f7-8901-bcde-f12345678901',
   750, 858.75, 108.75, 0.15, 16.31, 92.44, 0.15, 16.31, 733.69, false, 'active', now() - interval '1 month'),
  ('83333333-3333-4333-8333-333333333333', '22222222-2222-4222-8222-222222222222', 'f1a2b3c4-d5e6-7890-abcd-ef1234567890',
   500, 555, 55, 0.15, 8.25, 46.75, 0.15, 8.25, 491.75, false, 'active', now() - interval '15 days'),
  ('84444444-4444-4444-8444-444444444444', '22222222-2222-4222-8222-222222222222', 'f3c4d5e6-f7a8-9012-cdef-123456789012',
   1200, 1314, 114, 0.10, 11.40, 102.60, 0.15, 17.10, 1182.90, false, 'completed', now() - interval '3 months'),
  -- Ava Investor in Jack Row Corn Project (completed, fees owed)
  ('85555555-5555-4555-8555-555555555555', '11111111-1111-4111-8111-111111111111', 'f1a2b3c4-d5e6-7890-abcd-ef1234567890',
   800, 888, 88, 0.15, 13.20, 74.80, 0.15, 13.20, 786.80, false, 'completed', now() - interval '4 months')
ON CONFLICT (id) DO UPDATE SET
  amount = EXCLUDED.amount,
  expected_return = EXCLUDED.expected_return,
  gross_profit = EXCLUDED.gross_profit,
  investor_fee_rate = EXCLUDED.investor_fee_rate,
  investor_platform_fee = EXCLUDED.investor_platform_fee,
  net_profit = EXCLUDED.net_profit,
  farmer_fee_rate = EXCLUDED.farmer_fee_rate,
  farmer_platform_fee = EXCLUDED.farmer_platform_fee,
  farmer_payout = EXCLUDED.farmer_payout,
  loss_protection_applied = EXCLUDED.loss_protection_applied,
  status = EXCLUDED.status;

-- Configurable platform fee rules
INSERT INTO platform_fee_rules (id, audience, label, rate, minimum, maximum, sort_order) VALUES
  ('investor_low_roi', 'investor', 'Low ROI projects', 0.10, NULL, 10, 1),
  ('investor_medium_roi', 'investor', 'Medium ROI projects', 0.15, 10, 15, 2),
  ('investor_high_roi', 'investor', 'High ROI projects', 0.25, 15, NULL, 3),
  ('farmer_under_10k', 'farmer', 'Funding under $10,000', 0.05, NULL, 10000, 4),
  ('farmer_10k_to_50k', 'farmer', 'Funding $10,000-$50,000', 0.10, 10000, 50000, 5),
  ('farmer_above_50k', 'farmer', 'Funding above $50,000', 0.15, 50000, NULL, 6)
ON CONFLICT (id) DO UPDATE SET
  label = EXCLUDED.label,
  rate = EXCLUDED.rate,
  minimum = EXCLUDED.minimum,
  maximum = EXCLUDED.maximum,
  sort_order = EXCLUDED.sort_order,
  updated_at = now();

-- Progress updates
INSERT INTO progress_updates (farm_id, milestone, progress_percent, stage, health, weather, photo_url, video_url, document_url, yield_report, expense_report, notes) VALUES
  ('f1a2b3c4-d5e6-7890-abcd-ef1234567890', 'Growing', 55, 'Growing Stage', 'Excellent', 'Sunny',
   'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=600', NULL, NULL, NULL, 'Fertilizer and irrigation spend tracking within plan.', 'Crop height at 1.8m. On track for October harvest.'),
  ('f1a2b3c4-d5e6-7890-abcd-ef1234567890', 'Land Preparation', 20, 'Irrigation Complete', 'Good', 'Partly Cloudy',
   'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=600', NULL, NULL, NULL, 'Irrigation capex completed.', 'Irrigation system fully operational across all paddocks.'),
  ('f2b3c4d5-e6f7-8901-bcde-f12345678901', 'Planting', 35, 'Planting Stage', 'Good', 'Humid',
   'https://images.unsplash.com/photo-1594026112284-02bb6f3352fe?w=600', NULL, NULL, NULL, 'Seedling labor costs on budget.', 'Rice planting 80% complete across all paddies.'),
  ('f3c4d5e6-f7a8-9012-cdef-123456789012', 'Completed', 100, 'Completed Cycle', 'Excellent', 'Clear',
   'https://images.unsplash.com/photo-1516467508483-a7212febe31a?w=600', NULL, NULL, 'Final yield exceeded baseline by 6%.', 'Final feed and logistics costs reconciled.', 'Livestock project completed with payout ready for investors.'),
  ('f4d5e6f7-a8b9-0123-def0-234567890123', 'Land Preparation', 20, 'Land Preparation', 'Good', 'Dry',
   'https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=600', NULL, NULL, NULL, 'Land preparation expenses 5% above plan.', 'Land preparation underway for September harvest cycle.');

-- Reviews
INSERT INTO reviews (farmer_id, user_id, rating, comment, reviewer_name) VALUES
  ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', '11111111-1111-4111-8111-111111111111', 5,
   'Jack is exceptional. Regular updates, transparent communication, and returns ahead of schedule.',
   'Ava Investor'),
  ('b2c3d4e5-f6a7-8901-bcde-f12345678901', '11111111-1111-4111-8111-111111111111', 4,
   'Good communication throughout the season. ROI came in as expected.',
   'Ava Investor'),
  ('c3d4e5f6-a7b8-9012-cdef-123456789012', '22222222-2222-4222-8222-222222222222', 5,
   'Maria runs a top-class operation with reliable returns.',
   'Noah Investor');

-- Messages
INSERT INTO messages (investment_id, sender, body) VALUES
  ('81111111-1111-4111-8111-111111111111', 'farmer', 'Thanks for investing in the corn project. Irrigation is complete.'),
  ('81111111-1111-4111-8111-111111111111', 'investor', 'Great update, Jack. Looking forward to the next progress photo.'),
  ('82222222-2222-4222-8222-222222222222', 'farmer', 'Organic rice planting is moving on schedule this week.');
