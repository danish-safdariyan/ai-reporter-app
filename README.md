# AI-Powered Reporter

Complete software that compiles work from the last 3 weeks:

- **LAB 1** — API query: World Bank Indicators API (v2)
- **LAB 2** — Shiny app: query parameters, table, chart, CSV download
- **LAB 3** — AI reporting: generate summary from current data (Ollama local / Ollama Cloud / OpenAI)

One app: query a public API, display data in a Shiny interface, and use AI to generate reporting summaries.

## Setup

```bash
cd ai_reporter_app
pip install shiny pandas requests matplotlib python-dotenv
```

Optional: copy `.env.example` to `.env` and set `WORLD_BANK_API_KEY`, `OLLAMA_API_KEY`, or `OPENAI_API_KEY` if needed.

## Run

```bash
shiny run app.py
```

Open the URL in your browser (e.g. http://127.0.0.1:8000). Choose countries, indicator, and year range → **Run Query** → view data and chart → **Generate AI Report** to get an AI summary (requires Ollama running locally, or API keys in `.env` for cloud).

## Files

- `query.py` — World Bank API client (from Lab 1 / Lab 2)
- `ai_report.py` — Build summary from data and call Ollama/OpenAI (from Lab 3)
- `app.py` — Shiny UI and server (query + display + AI report)
