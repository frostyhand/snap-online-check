"""Code each answer (plain Gemini call with a JSON schema, no search, temperature 0).

For every answer: the stores and apps it names as places to order groceries with EBT, whether it says SNAP
can pay delivery or service fees, and whether it points the shopper to an official list. For the "check"
questions, also its verdict on the named retailer.

    .venv/bin/python -m study.extract --model MODEL
"""

import argparse
import hashlib
import json
import time

from study.config import DERIVED, RAW
from study.gemini import Gemini, QuotaStop, append_jsonl, read_jsonl

RUNS = RAW / "runs.jsonl"
CODES = DERIVED / "codes.jsonl"

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "stores": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "order": {"type": "INTEGER"},
                    "said_takes_ebt_online": {"type": "STRING", "enum": ["yes", "no", "unclear"]},
                },
                "required": ["name", "order", "said_takes_ebt_online"],
            },
        },
        "verdict": {"type": "STRING", "enum": ["yes", "no", "depends", "not_applicable"]},
        "fees": {"type": "STRING", "enum": ["snap_pays_fees", "fees_not_covered", "silent"]},
        "points_to_official": {"type": "BOOLEAN"},
    },
    "required": ["stores", "verdict", "fees", "points_to_official"],
}

INSTRUCTIONS = """Below is an AI assistant's answer to a shopper in {city}, {state} who receives SNAP (food stamps)
and asked: "{question}"

Code the answer exactly as written. Do not correct it or add knowledge of your own.

stores: every store, chain, website or delivery app the answer names as a place where the shopper could
  order groceries online (delivery or pickup). One entry per business, in the order first named (order
  starts at 1). Include examples inside lists ("stores like X or Y"). Do NOT include government offices,
  food banks, apps that only show a benefit balance, or unnamed store types ("local grocers").
  said_takes_ebt_online: "yes" if the answer says or clearly implies the shopper can pay with EBT online
  there; "no" if it says they cannot; "unclear" otherwise.
verdict: {verdict_rule}
fees: "snap_pays_fees" if the answer says or implies SNAP/EBT can pay delivery, service or other fees;
  "fees_not_covered" if it says those fees must be paid another way; "silent" if it does not say.
points_to_official: true if the answer tells the shopper to check USDA's list, the state SNAP agency, or the
  retailer's own website to confirm.

ANSWER:
{text}"""

VERDICT_CHECK = ('the answer\'s bottom line on whether the shopper can pay with EBT online at {retailer} '
                 'where they live: "yes", "no", or "depends" (only if it gives no bottom line and says it '
                 'varies or to check). Never "not_applicable".')
VERDICT_OPEN = '"not_applicable" (this was an open question).'


def done(path=CODES) -> set[str]:
    return {r["run_id"] for r in read_jsonl(path)}


def build(run: dict, retailer_name: str | None) -> str:
    rule = VERDICT_CHECK.format(retailer=retailer_name) if run["framing"] == "check" else VERDICT_OPEN
    return INSTRUCTIONS.format(city=run["city"], state=run["state"], question=run["prompt"],
                               verdict_rule=rule, text=run["text"])


def main(argv=None):
    from study.config import PANEL
    names = dict(PANEL)
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--gap", type=float, default=4.5)
    ap.add_argument("--shard", default="0/1", help="i/n: code only answers whose id hashes to shard i of n")
    a = ap.parse_args(argv)
    i_shard, n_shard = map(int, a.shard.split("/"))
    seen = done()
    runs = [r for r in read_jsonl(RUNS) if r.get("text") and r["id"] not in seen
            and int(hashlib.sha256(r["id"].encode()).hexdigest(), 16) % n_shard == i_shard]
    print(f"{len(runs)} answers to code")
    g = Gemini(a.model)
    for i, r in enumerate(runs, 1):
        try:
            out = g.generate(build(r, names.get(r.get("retailer"))), schema=SCHEMA, temperature=0)
            code = json.loads(out["text"])
        except QuotaStop as e:
            print(f"stopped: {e}")
            break
        except (RuntimeError, json.JSONDecodeError) as e:
            print(f"error on {r['id']}: {e}")
            continue
        append_jsonl(CODES, {"run_id": r["id"], "code_model": out.get("served_model") or a.model,
                             **code, "t": time.time()})
        print(f"[{i}/{len(runs)}] {r['id']}: {len(code.get('stores', []))} stores, verdict={code.get('verdict')}")
        time.sleep(a.gap)


if __name__ == "__main__":
    main()
