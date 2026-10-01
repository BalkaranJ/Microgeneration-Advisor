# Deploying SolarFit

The frontend is a static Vite build (Vercel or Netlify). The backend is a FastAPI service (Render or Fly.io). Set the cost guardrails below before the link goes public.

## 1. Cost guardrails (do these first)

1. **Google Cloud**: Billing > Budgets & alerts, add a budget with email alerts at 50%, 90%, 100%. Then APIs & Services > Solar API (and Maps Static API) > Quotas, and cap requests per day. Restrict the API key to those APIs only.
2. **Anthropic Console**: set a monthly spend limit on the workspace. Only matters if bill upload stays on.
3. **App-level limits** (built in, see `backend/ratelimit.py`). Defaults per IP: 10 assessments/hour, 20 roof images/hour, 60 geocodes/hour, 3 bill uploads/day. Global daily caps: 300 assessments, 300 roof images, 50 bill uploads. Override with env vars such as `RATE_LIMIT_ASSESS_PER_IP` and `RATE_LIMIT_ASSESS_GLOBAL_DAILY`.
4. Limits are in memory, so run a single backend instance (one uvicorn worker). A restart resets the counters, which is why the Google and Anthropic caps above matter.

## 2. Backend (Render)

1. New Web Service from the GitHub repo, root directory `backend`.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
4. Health check path: `/health`
5. Environment variables:

| Name | Value |
|---|---|
| `GOOGLE_SOLAR_API_KEY` | your key |
| `ANTHROPIC_API_KEY` | your key (can be omitted if bill upload is off) |
| `CORS_ORIGINS` | your frontend origin, e.g. `https://solarfit.ca` (comma separate more than one) |
| `ENABLE_BILL_UPLOAD` | `false` for the public demo |
| `TRUST_PROXY` | `true` (so limits use the real client IP behind Render's proxy) |
| `PYTHON_VERSION` | `3.12.3` |

Render's free tier sleeps when idle, so the first request after a quiet period takes about 30 seconds. A paid always-on instance avoids that.

## 3. Frontend (Vercel or Netlify)

1. Import the repo, root directory `frontend`, framework Vite, build `npm run build`, output `dist`.
2. Environment variables (set before building, they are baked in at build time):

| Name | Value |
|---|---|
| `VITE_API_URL` | your backend URL, e.g. `https://api.solarfit.ca` or the `onrender.com` URL |
| `VITE_ENABLE_BILL_UPLOAD` | `false` to match the backend |

## 4. Domain

Buy the domain at a registrar, then add it in the frontend host (apex or `www`) and optionally an `api.` subdomain on the backend host. Both hosts show the exact DNS records to add. HTTPS certificates are issued automatically. After the domain works, put the frontend origin into the backend's `CORS_ORIGINS`.

## 5. Check it

- `GET <backend>/health` returns `{"status":"ok"}`.
- Run one assessment end to end on the live site.
- Confirm the browser console shows no CORS errors.
