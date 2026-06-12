# CLAUDE.md — MyAgro

> Project guide for Claude Code. Read this fully before generating or editing any code.
> When a rule here conflicts with a default assumption, **this file wins**.

---

## 1. What we are building

**MyAgro** is a digital agricultural investment platform that connects investors directly with verified farmers. Investors browse farm projects, review AI-style risk analysis and farmer reputation, invest funds, track portfolio performance, monitor farm progress, and receive returns.

This repository is the **deployed, fully functional** implementation of the MyAgro MVP for the assignment. It must:

- Run live on **Vercel**.
- Persist real, user-submitted data in **Supabase** (PostgreSQL).
- Keep all secrets in **environment variables** — never hardcoded, never shipped to the browser.
- Be committed to **GitHub** with a clean, well-organised structure and a correct `.gitignore`.

### Grading-critical behaviours (do not break these)
1. Every screen must remain **functional end-to-end** — no dead buttons, no mock-only flows.
2. Data the user submits must be **saved to and read back from Supabase** (round-trip must be real).
3. The **Supabase service role key and DB connection string live only on the backend**. Never expose them in frontend code or commit them.
4. The full investment workflow (browse → invest → confirm → portfolio → returns) must work against the live database.

---

## 2. Installed Claude Code skills — when to use them

This project has the following skills installed. **Prefer them over working from memory.** They are doc-driven and version-aware, which matters because library APIs change.

| Skill | Use it for |
|-------|-----------|
| **supabase** (`supabase/agent-skills`) | ALL Supabase/Postgres work: schema design, SQL, RLS policies, client setup, secure key handling, performance/security review. It verifies against current Supabase docs first — follow its guidance over assumptions. |
| **vercel-deploy** (`vercel-labs/agent-skills`) | Deploying to Vercel and setting up git-linked deploys. Triggers on "deploy", "push live", "preview URL". |
| **tanstack-router** | All frontend routing and route/data-loading patterns. |
| **fastapi** | Building/editing backend endpoints, dependencies, and Pydantic v2 models. |
| **context7** | Pulling live docs for any library (FastAPI, TanStack, Supabase, Vercel) before writing version-specific code. Pair it with the supabase skill. |
| **codebase-memory** | Recalling prior decisions/conventions across sessions. Consult before re-deriving structure or re-asking settled questions. |

### Skill workflow rules
- Before writing any Supabase-specific code → engage the **supabase** skill (and **context7** for current API shapes). Do not hand-write SQL or client calls from memory.
- Before deploying → engage the **vercel-deploy** skill; it checks git remote + link state and pushes toward git-linked deploys (which we want for the demo).
- Before adding routes or data loaders → engage the **tanstack-router** skill.
- Before adding/changing endpoints → engage the **fastapi** skill.
- When unsure of a current API or config, prefer **context7** / the relevant skill over guessing.

---

## 3. Tech stack (do not substitute without being asked)

| Layer        | Technology                                                       |
|--------------|------------------------------------------------------------------|
| Frontend     | React 18 + Vite, **TanStack Router**, **TanStack Query**, Tailwind CSS |
| Backend      | Python 3.11 + FastAPI, Pydantic v2                               |
| DB client    | `supabase-py` (server-side, service role key)                    |
| Database     | Supabase (PostgreSQL)                                             |
| Hosting      | Vercel (frontend static build + Python serverless API)           |
| Validation   | Pydantic on the backend, lightweight checks on frontend          |

**No ORM / no Alembic for this assignment** — keep it simple. Talk to Supabase through the official `supabase-py` client, guided by the supabase skill. Schema lives in `db/schema.sql` and is applied via the Supabase SQL editor.

---

## 4. Repository structure

Generate and maintain this layout. Do not scatter files outside it.

```
myagro/
├── api/                       # Python (FastAPI) backend — deployed as Vercel serverless function
│   ├── index.py               # FastAPI app + Vercel entrypoint (exports `app`)
│   ├── db.py                  # Supabase client, built from env vars ONLY
│   ├── deps.py                # shared dependencies (client provider, error helpers)
│   ├── schemas.py             # Pydantic v2 request/response models
│   ├── routers/
│   │   ├── farms.py           # GET farms, GET farm by id
│   │   ├── farmers.py         # GET farmer profile + reviews
│   │   ├── investments.py     # POST invest, GET portfolio, returns
│   │   ├── progress.py        # GET farm progress updates
│   │   └── messages.py        # GET/POST investor–farmer messages
│   └── requirements.txt
│
├── frontend/                  # React + Vite app
│   ├── src/
│   │   ├── main.jsx           # mounts app + QueryClientProvider + RouterProvider
│   │   ├── router.jsx         # TanStack Router setup / route tree
│   │   ├── routes/            # one route component per screen (see §7)
│   │   ├── api/client.js      # fetch wrapper, reads VITE_API_BASE_URL
│   │   ├── queries/           # TanStack Query hooks (useFarms, useInvest, etc.)
│   │   ├── components/        # reusable UI
│   │   └── styles/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
├── db/
│   ├── schema.sql             # CREATE TABLE statements (run in Supabase SQL editor)
│   └── seed.sql               # demo farms/farmers so the app isn't empty
│
├── vercel.json                # routing: /api/* -> python, everything else -> SPA
├── .env.example               # documents required vars (NO real values)
├── .gitignore
├── README.md
├── CLAUDE.md                  # this file
└── PROMPTS.md                 # running log of prompts (see §12)
```

---

## 5. Security rules — non-negotiable

These are the highest-priority rules in this file. The **supabase** skill enforces the same patterns — defer to it on key handling.

- **Never hardcode** a Supabase URL, anon key, service role key, JWT secret, or Postgres connection string in any committed file.
- All secrets are read from environment variables at runtime via `os.environ` (backend) or `import.meta.env` (frontend build-time).
- The **`SUPABASE_SERVICE_ROLE_KEY` and `DATABASE_URL` are backend-only**. They must never appear in `frontend/`, in any `VITE_`-prefixed variable, or in network responses to the browser.
- The frontend talks to **our own `/api` backend**, not directly to Supabase with privileged keys. All writes go through the Python backend.
- `.env`, `.env.local`, and `.env.*.local` are **git-ignored**. Only `.env.example` (with empty/placeholder values) is committed.
- Before creating or editing `.gitignore`, confirm it ignores: `.env`, `.env*.local`, `node_modules/`, `__pycache__/`, `*.pyc`, `.vercel/`, `dist/`, `.DS_Store`.
- If you ever notice a secret about to be written into a tracked file, **stop and flag it** instead of proceeding.

### Required environment variables

Backend (set in Vercel project settings, server-side):
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=     # secret — backend only
```

Frontend (build-time, safe to expose, must be prefixed VITE_):
```
VITE_API_BASE_URL=/api          # points at our Python backend
```

`.env.example` must list these names with **blank** values and a one-line comment each. Never put real keys in it.

---

## 6. Database schema (Supabase / PostgreSQL)

Keep the canonical schema in `db/schema.sql`. Use the **supabase** skill to author and review it. Tables reflect the MVP domain:

- **users** — `id (uuid pk)`, `name`, `email (unique)`, `phone`, `location`, `created_at`
- **farmers** — `id (uuid pk)`, `name`, `verified (bool)`, `rating (numeric)`, `completed_projects (int)`, `on_time_rate (int)`, `risk_classification (text)`
- **farms** — `id (uuid pk)`, `farmer_id (fk → farmers)`, `crop_type`, `location`, `expected_roi (numeric)`, `risk_level (text)`, `success_rate (int)`, `duration_months (int)`, `harvest_date (date)`, `status (text)`, `created_at`
- **investments** — `id (uuid pk)`, `user_id (fk → users)`, `farm_id (fk → farms)`, `amount (numeric)`, `expected_return (numeric)`, `status (text default 'active')`, `created_at`
- **progress_updates** — `id (uuid pk)`, `farm_id (fk → farms)`, `stage`, `health`, `weather`, `photo_url`, `created_at`
- **messages** — `id (uuid pk)`, `investment_id (fk → investments)`, `sender (text)`, `body (text)`, `created_at`
- **reviews** — `id (uuid pk)`, `farmer_id (fk → farmers)`, `user_id (fk → users)`, `rating (int)`, `comment`, `created_at`

Conventions:
- Use `uuid` primary keys with `gen_random_uuid()` defaults.
- Use `timestamptz` with `now()` defaults for `created_at`.
- Add foreign keys explicitly; index `farm_id` and `user_id` on `investments`.
- Provide `db/seed.sql` with at least the two demo projects from the MVP (Jack Row — Corn, ROI 11%, success 92%, low risk; John Spay — Organic Rice, ROI 14.5%, moderate) plus their farmer rows, so the live app shows real data immediately.

### Business rules to enforce in the backend
- Investment `amount` must be **>= 100 and <= 10000**. Reject otherwise with HTTP 422.
- `expected_return = round(amount * (1 + expected_roi/100), 2)`.
- Never trust the client's computed return — recompute it server-side from the farm's ROI before inserting.

---

## 7. Frontend conventions

- One route component per screen, in `frontend/src/routes/`. Cover the full MVP journey:
  `Login`, `ExploreFarms`, `FarmDetail` (risk analysis + farmer profile), `Invest`, `InvestmentConfirmation`, `Portfolio`, `FarmProgress`, `Returns`, `Messages`.
- **Routing: TanStack Router** (use the tanstack-router skill). Keep the route tree in `src/router.jsx`. Route loaders may prefetch data where it helps; otherwise fetch in the component via Query hooks.
- **Server state: TanStack Query.** All reads are `useQuery` hooks and all writes are `useMutation` hooks, defined in `src/queries/`. Hooks call the thin fetch layer in `src/api/client.js` (which prepends `import.meta.env.VITE_API_BASE_URL`). **No raw `fetch` scattered in components.**
- Loading and error states come from Query state (`isPending`, `isError`) — render them on every data-driven screen. No blank screens on slow networks.
- Invalidate the relevant queries after a mutation (e.g. after investing, invalidate `portfolio`) so the UI reflects fresh DB data.
- Styling: Tailwind utility classes. Keep the dark/clean aesthetic; don't introduce a second styling system.
- Guest access: allow browsing farms without login, but require a (simple) identity before investing so the investment can be tied to a `user_id`.
- Do **not** use `localStorage` for secrets. Session/auth state can live in React state or context for this assignment.

---

## 8. Backend conventions (FastAPI)

Use the **fastapi** skill for endpoint/dependency/model work and **context7** for current FastAPI/Pydantic v2 APIs.

- `api/index.py` builds the FastAPI `app`, enables CORS for the frontend origin, and includes the routers. Vercel imports `app` from this module.
- Build the Supabase client **once** in `api/db.py` from `os.environ["SUPABASE_URL"]` and `os.environ["SUPABASE_SERVICE_ROLE_KEY"]` (let the supabase skill guide client setup). Fail loudly at startup if either is missing.
- Every request/response is typed with a **Pydantic v2** model in `schemas.py`. No raw dicts crossing the API boundary.
- Routers are thin: validate → call Supabase → shape response. Keep query logic readable.
- Return proper status codes: `200` reads, `201` creates, `422` validation errors, `404` missing resources, `500` only for genuine server faults (with a safe message — never leak stack traces or keys).
- Endpoints (REST, JSON):
  - `GET /api/farms` (supports `?crop=` and `?sort=roi` filters)
  - `GET /api/farms/{id}`
  - `GET /api/farmers/{id}`
  - `POST /api/investments`  → validates amount, computes return, inserts, returns confirmation
  - `GET /api/portfolio?user_id=`
  - `GET /api/farms/{id}/progress`
  - `GET /api/investments/{id}/messages` / `POST /api/investments/{id}/messages`
- All DB writes are server-side only. The frontend never holds a privileged key.

---

## 9. Deployment (Vercel)

Use the **vercel-deploy** skill for deploys; commit to GitHub first so it can set up git-linked deployments.

- Single Vercel project serving the SPA and the Python API.
- `vercel.json` rewrites `/api/(.*)` to the Python serverless function and routes everything else to the SPA `index.html`.
- Frontend build: Vite (`npm run build` → `dist`).
- Backend: Python runtime picks up `api/index.py`; dependencies from `api/requirements.txt` (`fastapi`, `supabase`, `pydantic`).
- Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `VITE_API_BASE_URL` in **Vercel → Project → Settings → Environment Variables** before deploying. Do not rely on a local `.env` being present in the cloud.
- After deploy, verify the full workflow against the live URL and confirm a fresh row appears in the Supabase Table Editor.

---

## 10. Coding standards

- Prefer clear, small functions over clever one-liners. Name things for what they hold.
- No dead code, no commented-out blocks left behind, no `console.log` / `print` debugging in committed code.
- Frontend: functional components and hooks only.
- Backend: type hints everywhere; `async def` handlers.
- Keep responses and errors consistent in shape so the frontend can rely on them.
- When unsure about a domain rule, follow the MVP document and §6 here rather than inventing behaviour.

---

## 11. Git & workflow

- Commit in small, meaningful units with clear messages (e.g. `feat(api): add investment endpoint with amount validation`).
- Never commit `.env`, build artefacts, `node_modules/`, or `__pycache__/`.
- The repo must read cleanly top to bottom for a marker: `README.md` explains setup + run + deploy; structure matches §4.
- Decide public vs private repo with the user; default to **private** unless told otherwise, and ensure the assignment grader has access.

---

## 12. Prompt logging (assignment deliverable)

The assignment requires a record of the prompts used to build the app.

- Maintain **`PROMPTS.md`** in the repo root.
- **After completing any task driven by a user prompt, append an entry** to `PROMPTS.md` in this format:

```
## [YYYY-MM-DD HH:MM]
**Prompt:** <the user's prompt, verbatim or lightly trimmed>
**Outcome:** <one-line summary of what was built/changed and which files>
```

- Keep entries in chronological order, newest at the bottom. Do not delete past entries.
- This file is part of the submission appendix — treat it as a deliverable, not scratch notes.

---

## 13. Do / Don't quick reference

**Do**
- Route every secret through env vars.
- Use the installed skills (§2) instead of working from memory.
- Recompute financial returns server-side.
- Keep all screens functional against the live Supabase data.
- Update `PROMPTS.md` after each prompt-driven change.
- Validate investment amount (100–10000) on the backend.

**Don't**
- Hardcode or expose the service role key / DB connection string.
- Let the frontend write to Supabase with privileged keys.
- Ship mock-only flows where the assignment expects real persistence.
- Commit `.env` or build artefacts.
- Swap the specified stack (React / TanStack / FastAPI / Supabase / Vercel) without being asked.
