# Documentation (copy this section into ai_reporter.docx)

---

## Data Summary (API data columns)

| Column name     | Data type | Description |
|-----------------|-----------|-------------|
| country_id      | string    | World Bank country code (e.g. USA, GBR, FRA). |
| country_name    | string    | Full country name (e.g. United States, United Kingdom). |
| indicator_id    | string    | World Bank indicator code (e.g. NY.GDP.PCAP.CD). |
| indicator_name  | string    | Full indicator name (e.g. GDP per capita (current US$)). |
| year            | numeric   | Year of the observation. |
| value           | numeric   | Value of the indicator for that country and year; may be null if missing. |

---

## Technical Details

- **API:** World Bank Indicators API (v2). Base URL: `https://api.worldbank.org/v2`. Endpoint: `GET /country/{country_codes}/indicator/{indicator_code}` with query parameters `date` (year range), `format=json`, and `per_page`.
- **API key:** Optional. The World Bank API often works without a key. If you use one, set the env var `WORLD_BANK_API_KEY` in a `.env` file.
- **AI report:** The app tries, in order: (1) local Ollama, (2) Ollama Cloud (if `OLLAMA_API_KEY` is set), (3) OpenAI (if `OPENAI_API_KEY` is set). Set these in `.env` only if you use cloud AI.
- **Packages:** `shiny`, `pandas`, `requests`, `matplotlib`, `python-dotenv`, `markdown-it-py` (see `requirements.txt`).
- **File structure:**
  - `app.py` — Shiny UI and server (query form, table, chart, download, AI report).
  - `query.py` — World Bank API client (URL building, fetch, normalize to table, cache).
  - `ai_report.py` — Builds a short summary from the data table and calls Ollama/OpenAI.
  - `requirements.txt` — Python dependencies.
  - `.env.example` — Example env vars (copy to `.env` and fill in if needed).
  - `.do/app.yaml` — DigitalOcean App Platform run config (for deployment).

---

## Usage Instructions

**1. Install dependencies**

From the project folder (the one that contains `app.py` and `requirements.txt`):

```
cd ai_reporter_app
pip install -r requirements.txt
```

**2. (Optional) API keys**

- Copy `.env.example` to `.env`.
- Edit `.env`: add `WORLD_BANK_API_KEY` only if you use one; add `OLLAMA_API_KEY` or `OPENAI_API_KEY` only if you want cloud AI reports. You can leave `.env` empty and the app still runs (World Bank without a key; AI report only if Ollama is running locally).

**3. Run the app**

```
shiny run app.py
```

Open the URL shown in the terminal (e.g. http://127.0.0.1:8000). Choose countries, indicator, and year range, click **Run Query**, then **Generate AI Report** for a summary (requires Ollama running locally or the optional API keys above).
