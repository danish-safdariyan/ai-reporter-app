"""
AI report generation from World Bank data.
From LAB_ai_reporter: build summary from DataFrame, call Ollama/OpenAI, return report text.
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd
import requests


def dataframe_to_summary(df: pd.DataFrame) -> str:
    """Build by-country summary stats from World Bank-style DataFrame for AI consumption."""
    if df is None or df.empty:
        return "No data available."
    if "country_name" not in df.columns or "value" not in df.columns:
        return "No data available."
    by_country = df.dropna(subset=["value"]).groupby("country_name")["value"]
    lines = []
    for country in sorted(by_country.groups.keys()):
        vals = by_country.get_group(country)
        n = len(vals)
        avg, mn, mx = vals.mean(), vals.min(), vals.max()
        lines.append(f"{country}: n={n} years, mean={avg:.2f}, min={mn:.2f}, max={mx:.2f}")
    return "\n".join(lines) if lines else "No data available."


def build_prompt(data_summary: str, indicator_name: str) -> str:
    """Prompt for AI: summary + format instructions."""
    return f"""You are a data analyst. Below are summary statistics from the World Bank for the indicator "{indicator_name}".

Data (by country):
{data_summary}

Write a short report (2–3 sentences) summarizing the data, then list 3–5 bullet-point insights, and end with 1–2 brief recommendations. Use plain language. Keep the total response under 150 words."""


def _query_ollama_local(prompt: str, model: str = "gemma3:latest", port: int = 11434) -> str:
    url = f"http://localhost:{port}/api/generate"
    body = {"model": model, "prompt": prompt, "stream": False}
    resp = requests.post(url, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "")


def _query_ollama_cloud(prompt: str, api_key: str) -> str:
    url = "https://ollama.com/api/chat"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": "gpt-oss:20b-cloud", "messages": [{"role": "user", "content": prompt}], "stream": False}
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "")


def _query_openai(prompt: str, api_key: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_report(
    df: pd.DataFrame,
    indicator_name: str,
    ollama_model: str = "gemma3:latest",
) -> str:
    """
    Generate AI report from World Bank DataFrame.
    Tries Ollama local, then Ollama Cloud (OLLAMA_API_KEY), then OpenAI (OPENAI_API_KEY).
    Returns report text or raises/returns error message.
    """
    if df is None or df.empty:
        return "No data available. Run a query first."
    data_summary = dataframe_to_summary(df)
    if not data_summary or data_summary == "No data available.":
        return "No data available to summarize."
    prompt = build_prompt(data_summary, indicator_name)

    report: Optional[str] = None
    err: Optional[str] = None

    try:
        report = _query_ollama_local(prompt, model=ollama_model)
    except Exception as e:
        err = str(e)

    if report is None and os.getenv("OLLAMA_API_KEY"):
        try:
            report = _query_ollama_cloud(prompt, os.getenv("OLLAMA_API_KEY", ""))
        except Exception as e:
            err = str(e)

    if report is None and os.getenv("OPENAI_API_KEY"):
        try:
            report = _query_openai(prompt, os.getenv("OPENAI_API_KEY", ""))
        except Exception as e:
            err = str(e)

    if report:
        return report
    return f"AI report failed. (Ollama local: {err or 'not running'}. Set OLLAMA_API_KEY or OPENAI_API_KEY in .env for cloud.)"
