# MyAgro

MyAgro is a full-stack agricultural investment platform connecting investors with verified farmers. Investors browse farm projects, analyse AI-generated risk scores, invest funds, track returns, and message farmers directly. Farmers manage their campaigns, monitor funding progress, and receive payouts. Admins oversee platform analytics, user activity, and fee configuration.

---

## Demo Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@myagro.test | admin@myagro.test |
| Farmer | farmer01@myagro.demo | farmer01@myagro.demo |
| Investor | investor01@myagro.demo | investor01@myagro.demo |

---

## How the System Works

```
Browser → React SPA (TanStack Router) → FastAPI backend → Supabase PostgreSQL
```

1. **Authentication** — Users register or log in at `/`. The backend validates credentials, detects the role (`investor`, `farmer`, `admin`), and returns a session. The frontend stores the session and redirects to the appropriate dashboard.
2. **Farm discovery** — Investors browse `GET /api/farms` (filterable by crop type or sorted by ROI). Each farm card shows the risk level computed by the Risk Engine.
3. **Investing** — The investor submits an amount. The backend validates the range (₵100–₵10,000), looks up the farm's ROI, and recomputes expected return, gross profit, platform fee, and net profit server-side before inserting into Supabase. The client's numbers are never trusted.
4. **Dashboards** — Each role gets a dedicated dashboard endpoint that aggregates data from Supabase and runs the Risk Engine on every farm before returning the response.
5. **Messaging** — Investors and farmers exchange messages per investment thread via `GET/POST /api/investments/{id}/messages`.
6. **Progress updates** — Farmers post field stage, crop health, and weather reports; investors see them on `GET /api/farms/{id}/progress`.

---

## AI Risk Analysis System

The risk engine lives in `backend/risk_engine/service.py`. It produces a deterministic, weighted score (0–100) for every farm — no external LLM is called; the "AI-style" analysis is a rule-based model trained on the platform's domain knowledge.

### Scoring factors and weights

| Factor | Weight |
|---|---|
| Farmer reputation score | 30% |
| Historical project success rate | 25% |
| Project completion history | 20% |
| Investor ratings (reviews) | 15% |
| Active project load | 10% |

### Adjustments applied on top of the base score

- **Crop-specific risk** — each crop type carries a fixed adjustment (e.g. corn/wheat +2, potato −3) from `CROP_RISK_ADJUSTMENTS`.
- **Funding size** — smaller funding goals (<= ₵10k) raise the score slightly; very large goals (> ₵500k) lower it.
- **Verification status** — verified farmers: +3; pending verification: −3.
- **Failure penalty** — −8 per previously failed project, capped at −24.
- **Seasonal timing** — harvest date relative to the current season for the crop type.

The final score maps to a risk level: **LOW** (≥ 70), **MEDIUM** (40–69), **HIGH** (< 40).

### AI narrative insight

`backend/ai_insights/service.py → project_investment_insight()` converts the numeric result into a human-readable summary:

> *"Jack Row has completed 8 projects with 92% success rate… this project is LOW RISK (78/100) and is suitable for conservative investors."*

This narrative is returned alongside the score in every farm detail and dashboard response.

### Reputation engine

`backend/reputation_engine/service.py → build_reputation_profile()` aggregates a farmer's verified status, star rating from reviews, completed project count, and on-time delivery rate into a single reputation object. The Risk Engine consumes this object as its primary input.

---

## Dashboard Systems

### Investor Dashboard (`/investor/dashboard`)

**Backend**: `GET /api/dashboards/investor/{user_id}`
**Frontend**: `frontend/src/routes/InvestorDashboard.jsx`

What it shows:
- Portfolio totals — total invested, expected returns, gross profit, platform fee, net profit
- Average ROI across all active investments
- Allocation breakdown by crop type and by farmer (charts)
- Cumulative expected-returns growth curve over time
- Platform-wide context: most invested farmer and crop

The backend fetches the investor's investments with nested farm and farmer data, then runs `_portfolio_from_items()` to aggregate all financial figures.

---

### Farmer Dashboard (`/farmer/dashboard`)

**Backend**: `GET /api/dashboards/farmer/{farmer_id}`
**Frontend**: `frontend/src/routes/FarmerDashboard.jsx`

What it shows:
- Reputation score and overall star rating
- Active and completed project counts, unique investor count
- Per-project: total raised, funding progress, platform fee deducted, net payout, risk score and level
- Revenue trend across projects
- Top 5 most active investors by amount

The backend fetches the farmer's farms, runs `score_project_risk()` on each, and aggregates investment totals to compute farmer payout figures.

---

### Admin Dashboard (`/admin/dashboard`)

**Backend**: `GET /api/dashboards/admin?admin_id={id}`
**Frontend**: `frontend/src/routes/AdminDashboard.jsx`

What it shows:
- Platform-wide totals — total commission earned, investment volume, farmer payouts, investor profit
- Risk distribution across all projects (LOW / MEDIUM / HIGH counts)
- Revenue by month and growth trends
- Farmer performance rankings (top and lowest by reputation)
- Most invested farmers, crops, and investors
- Project success rates with risk levels
- Risk score trends over time (average per month)
- Fee rule management (investor and farmer tier configuration)

The backend fetches all users, farmers, farms, investments, and reviews, runs the Risk Engine on every farm, then aggregates everything into `AdminTotals` and `AdminAnalytics` Pydantic models before returning.

**Access**: Admin login requires email + access code (`POST /api/auth/admin/login`). The access code is set in the backend environment — it is never exposed to the browser.

---

## Platform Fees

Fees are configured in `backend/config.py` from environment variables and recomputed server-side on every investment:

- **Investor fee** — percentage of gross investor profit taken by MyAgro.
- **Farmer fee** — percentage of the investment amount deducted before farmer payout.

Both are stored on the investment row alongside the net figures so the audit trail is permanent.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite, TanStack Router, TanStack Query, Tailwind CSS |
| Backend | Python 3.11 + FastAPI, Pydantic v2 |
| Database | Supabase PostgreSQL via server-side `supabase-py` |
| Hosting | Vercel (static SPA + Python serverless API) |
| E2E Tests | Playwright |

---

## Project Structure

```text
myagro/
  api/
    index.py              # Vercel shim importing backend.index:app
    requirements.txt
  backend/
    index.py              # FastAPI app, CORS, router registration
    config.py             # fee rates, admin config from env vars
    db.py                 # Supabase service-role client (env vars only)
    schemas.py            # Pydantic v2 request/response models
    routers/              # auth, dashboards, farms, farmers, investments, messages, progress
    risk_engine/          # score_project_risk() — weighted scoring model
    ai_insights/          # project_investment_insight() — narrative summary
    reputation_engine/    # build_reputation_profile() — farmer reputation aggregation
    profit_engine/        # fee and payout calculations
  frontend/
    src/
      router.jsx
      routes/             # Login, ExploreFarms, FarmDetail, Invest, InvestmentConfirmation,
      |                   # Portfolio, FarmProgress, Returns, Messages,
      |                   # InvestorDashboard, FarmerDashboard, AdminDashboard
      context/            # AuthContext — session, role detection, persist/restore
      queries/            # TanStack Query hooks (useFarms, useInvest, useDashboards, …)
      api/client.js       # fetch wrapper, prepends VITE_API_BASE_URL
    e2e/                  # Playwright tests (mocked /api responses)
  db/
    schema.sql            # CREATE TABLE statements — run in Supabase SQL editor
    seed.sql              # demo farmers, farms, investments, progress, messages, reviews
  vercel.json             # /api/* → Python function; everything else → SPA index.html
```

---

## Environment Variables

Backend (set in Vercel project settings, server-side only):

```bash
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=     # never exposed to the browser
MYAGRO_INVESTOR_FEE_RATE=0.10
MYAGRO_FARMER_FEE_RATE=0.03
CORS_ORIGINS=http://localhost:5173
```

Frontend (build-time, safe to expose):

```bash
VITE_API_BASE_URL=/api
```

---

## Supabase Setup

1. Create a Supabase project.
2. Run `db/schema.sql` in the Supabase SQL editor.
3. Run `db/seed.sql` for demo data (farmers, farms, investments, progress, messages, reviews).
4. Set the backend env vars above locally and in Vercel.

RLS is enabled on all app tables. The browser never calls Supabase directly — all reads and writes go through the FastAPI backend using the service role key.

---

## Local Development

Backend:

```bash
pip install -r backend/requirements.txt
uvicorn backend.index:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Set `frontend/.env` for local dev:

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## Testing

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run test:e2e
npm run build
```

The Playwright suite builds the Vite app and runs against a local production preview. Tests mock `/api` responses so all role flows (investor, farmer, admin, investment) can be verified without live Supabase credentials.

---

## Deployment

1. Push the repo to GitHub.
2. Import the repo into Vercel.
3. Set all environment variables in Vercel → Project → Settings → Environment Variables.
4. Deploy. `vercel.json` builds `frontend/dist`, routes `/api/*` to `api/index.py`, and rewrites all SPA routes to `index.html`.

After deploying, verify a full investment round-trip and confirm the new row appears in the Supabase Table Editor.
