# Microgeneration Readiness Advisor — Frontend

React + Vite single-page app. Walks the user through a conversational,
one-question-at-a-time form (address, technology type, usage, system size,
customer type) and calls the FastAPI backend's `/assess` endpoint to render
a scored recommendation.

```bash
npm install
npm run dev
```

Expects the backend running on `http://localhost:8000` (see `../backend` and
`../start.ps1`).
