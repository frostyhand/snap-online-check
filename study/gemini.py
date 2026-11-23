"""Gemini API client.

Cost rules:
* Calls with search grounding are billed on paid tiers; set DAILY_CAP to what you are willing to spend.
* A local ledger counts calls per UTC day and refuses to go past DAILY_CAP (a cost guard).
* A daily or monthly quota 429 stops the run; only per-minute 429s are retried.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from study.config import ENV_FILE, RAW, SIBLING

BASE = "https://generativelanguage.googleapis.com/v1beta"
LEDGER = RAW / "calls.jsonl"
# Main Street Share uses the same key, so both ledgers count toward the daily cap.
LEDGERS = [LEDGER, SIBLING / "data" / "raw" / "calls.jsonl"]
DAILY_CAP = {"grounded": 1200, "plain": 1500}


class QuotaStop(RuntimeError):
    """Daily or monthly free quota reached (by Google or by the local cap). Resume another day."""


def load_env(paths: tuple[Path, ...] = (ENV_FILE, SIBLING / ".env")) -> None:
    # Falls back to a sibling project's .env when this folder has none.
    for path in paths:
        if path.exists():
            _load(path)


def _load(path: Path) -> None:
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def calls_today(kind: str, paths: list[Path] = LEDGERS) -> int:
    d = today_utc()
    return sum(1 for p in paths for r in read_jsonl(p) if r.get("day") == d and r.get("kind") == kind)


def is_daily_quota(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("perday", "per day", "per_day", "monthly", "per month", "permonth"))


class Gemini:
    def __init__(self, model: str, timeout: float = 180):
        load_env()
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise SystemExit("GEMINI_API_KEY missing: add it to snap-online-check/.env or main-street-share/.env (see README)")
        self.model = model
        self.http = httpx.Client(timeout=timeout, headers={"x-goog-api-key": key})
        self.lock = threading.Lock()

    def list_models(self) -> list[dict]:
        r = self.http.get(f"{BASE}/models", params={"pageSize": 200})
        r.raise_for_status()
        return r.json().get("models", [])

    def _guard(self, kind: str) -> None:
        if calls_today(kind) >= DAILY_CAP[kind]:
            raise QuotaStop(f"local daily cap reached for {kind} calls ({DAILY_CAP[kind]})")

    def generate(self, prompt: str, *, system: str | None = None, grounded: bool = False,
                 schema: dict | None = None, temperature: float | None = None, tries: int = 6) -> dict:
        kind = "grounded" if grounded else "plain"
        body: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if grounded:
            body["tools"] = [{"google_search": {}}]
        cfg = {}
        if temperature is not None:
            cfg["temperature"] = temperature
        if schema is not None:
            cfg["responseMimeType"] = "application/json"
            cfg["responseSchema"] = schema
        if cfg:
            body["generationConfig"] = cfg
        last = None
        for attempt in range(tries):
            with self.lock:
                self._guard(kind)
                append_jsonl(LEDGER, {"t": time.time(), "day": today_utc(), "kind": kind, "model": self.model})
            t0 = time.perf_counter()
            try:
                r = self.http.post(f"{BASE}/models/{self.model}:generateContent", json=body)
            except httpx.HTTPError as e:
                last = f"{type(e).__name__}: {str(e)[:200]}"
                time.sleep(min(90, 10 * 2 ** attempt))
                continue
            if r.status_code == 429:
                if is_daily_quota(r.text):
                    raise QuotaStop(f"Google quota: {r.text[:400]}")
                last = f"HTTP 429: {r.text[:300]}"
                time.sleep(min(90, 15 * 2 ** attempt))
                continue
            if r.status_code in (500, 502, 503, 504):
                last = f"HTTP {r.status_code}: {r.text[:300]}"
                time.sleep(min(90, 10 * 2 ** attempt))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:600]}")
            d = r.json()
            cands = d.get("candidates") or []
            if not cands:
                last = f"no candidates: {json.dumps(d.get('promptFeedback'))[:300]}"
                time.sleep(5)
                continue
            c = cands[0]
            text = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts", [])
                           if not p.get("thought"))
            gm = c.get("groundingMetadata") or {}
            return {
                "text": text,
                "finish_reason": c.get("finishReason"),
                "served_model": d.get("modelVersion"),
                "search_queries": gm.get("webSearchQueries") or [],
                "sources": [{"title": (ch.get("web") or {}).get("title"), "uri": (ch.get("web") or {}).get("uri")}
                            for ch in gm.get("groundingChunks") or []],
                "usage": d.get("usageMetadata"),
                "latency_ms": round((time.perf_counter() - t0) * 1000),
            }
        raise RuntimeError(f"{self.model} failed after {tries} tries: {last}")
