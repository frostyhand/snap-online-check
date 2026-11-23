"""Send the wave's shopper questions to Gemini with Google Search grounding. Resumable.

    .venv/bin/python -m study.run --model MODEL [--place il tx] [--framing where check] [--limit 20]
"""

import argparse
import hashlib
import time

from study.config import RAW, prompts
from study.gemini import Gemini, QuotaStop, append_jsonl, read_jsonl

RUNS = RAW / "runs.jsonl"


def done_ids(path=RUNS) -> set[str]:
    return {r["id"] for r in read_jsonl(path) if r.get("text")}


def select(items, place=None, framing=None, retailer=None):
    return [p for p in items
            if (not place or p["place"] in place) and (not framing or p["framing"] in framing)
            and (not retailer or p["retailer"] in retailer)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--place", nargs="*")
    ap.add_argument("--framing", nargs="*")
    ap.add_argument("--retailer", nargs="*")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--gap", type=float, default=7.0, help="seconds between calls (free tier is per-minute limited)")
    a = ap.parse_args(argv)

    todo = [p for p in select(prompts(), a.place, a.framing, a.retailer) if p["id"] not in done_ids()]
    # stable shuffle, so a run cut short by the daily quota still covers places and framings evenly
    todo.sort(key=lambda p: hashlib.sha256(p["id"].encode()).hexdigest())
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(todo)} prompts to run")
    g = Gemini(a.model)
    n = 0
    for p in todo:
        try:
            out = g.generate(p["prompt"], system=p["system"], grounded=True)
        except QuotaStop as e:
            print(f"stopped: {e}")
            break
        except RuntimeError as e:
            print(f"error on {p['id']}: {e}")
            append_jsonl(RUNS, {**p, "model": a.model, "error": str(e)[:500], "t": time.time()})
            continue
        append_jsonl(RUNS, {**p, "model": a.model, "t": time.time(), **out})
        n += 1
        print(f"[{n}/{len(todo)}] {p['id']} sources={len(out['sources'])} chars={len(out['text'])}")
        time.sleep(a.gap)
    print(f"done: {n} new runs")


if __name__ == "__main__":
    main()
