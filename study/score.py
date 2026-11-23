"""Score coded answers against the answer key, apply the hand check, and write results/summary.md.

The answer key is state level, so two city-level layers correct it: a hand check of every disagreement
(data/reference/adjudications.csv) and a city coverage table saying whether each chain has a store serving
each city (data/reference/city/*.csv). Final outcomes use both (`final`, `truth_final` in checks.csv);
outcomes against the state key alone are kept as `outcome`.

    .venv/bin/python -m study.score
"""

import csv
from collections import Counter, defaultdict

from study.config import DERIVED, PANEL, RAW, REFERENCE, RESULTS
from study.gemini import read_jsonl
from study.reference import city_serves, panel_key, panel_truth, policies, usda_truth, verify

RUNS = RAW / "runs.jsonl"
CODES = DERIVED / "codes.jsonl"
ADJ = REFERENCE / "adjudications.csv"


def adjudications(path=ADJ) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open() as fh:
        return {r["run_id"]: r for r in csv.DictReader(fh)}


def final_truth(truth: str, verdict: str, adj: dict | None, serves: str | None) -> str:
    """The right answer for this shopper in this city: the state-level key, corrected by the hand check of
    disagreements and by the city coverage table. Returns yes/no/unclear (or banner)."""
    if truth == "banner":
        return truth
    if adj:
        right = adj["assistant_right"]
        if right == "yes" and verdict in ("yes", "no"):
            return verdict
        if right == "no" and verdict in ("yes", "no"):
            return "no" if verdict == "yes" else "yes"
        return "unclear"
    if truth == "yes" and serves == "no":
        return "no"
    if truth == "yes" and serves == "unclear":
        return "unclear"
    return truth


def outcome_for(verdict: str, truth: str) -> str:
    if truth == "banner":
        return "banner"
    if truth == "unclear":
        return "unclear"
    if verdict == "depends":
        return "hedged"
    if verdict == truth:
        return "correct"
    if verdict in ("yes", "no"):
        return "false_" + verdict
    return "uncoded"


def joined(runs: list[dict], codes: list[dict]) -> list[dict]:
    by = {c["run_id"]: c for c in codes}
    return [{**r, "code": by[r["id"]]} for r in runs if r.get("text") and r["id"] in by]


def store_rows(items: list[dict]) -> list[dict]:
    """One row per store named in an open answer ("where", "nocar"), with its key status (city-aware)."""
    out = []
    for it in items:
        if it["framing"] == "check":
            continue
        for s in it["code"].get("stores", []):
            out.append({"run_id": it["id"], "place": it["place"], "page": it["page"], "framing": it["framing"],
                        "order": s.get("order"), "name": s["name"], "said": s.get("said_takes_ebt_online"),
                        "status": _city_status(verify(s["name"], it["page"], it["state"]), s["name"], it["place"])})
    return out


def _city_status(status: str, name: str, place: str) -> str:
    """A store that takes EBT online in the state but has no store serving the shopper's city is wrong too."""
    if status != "ok":
        return status
    serves = city_serves(panel_key(name), place)
    return {"no": "wrong_city", "unclear": "city_unclear"}.get(serves, status)


def open_measures(items: list[dict]) -> dict:
    rows = store_rows(items)
    endorsed = [r for r in rows if r["said"] == "yes" and r["status"] != "platform"]
    scored = [r for r in endorsed if r["status"] in ("ok", "usda_listed", "wrong", "wrong_city")]
    wrong = [r for r in scored if r["status"] in ("wrong", "wrong_city")]
    open_items = [it for it in items if it["framing"] != "check"]
    fees = Counter(it["code"].get("fees") for it in open_items)
    answers_with_wrong = {r["run_id"] for r in wrong}
    return {
        "answers": len(open_items),
        "stores_named": len(rows),
        "stores_endorsed": len(endorsed),
        "endorsed_wrong": len(wrong),
        "endorsed_wrong_city": sum(r["status"] == "wrong_city" for r in wrong),
        "endorsed_city_unclear": sum(r["status"] == "city_unclear" for r in endorsed),
        "share_endorsed_wrong": len(wrong) / len(scored) if scored else None,
        "endorsed_unverified": sum(r["status"] == "unverified" for r in endorsed),
        "answers_with_a_wrong_store": len(answers_with_wrong),
        "share_answers_with_wrong": len(answers_with_wrong) / len(open_items) if open_items else None,
        "banner_mentions": sum(r["status"] == "banner" for r in endorsed),
        "platform_mentions": sum(r["status"] == "platform" for r in rows),
        "fees_snap_pays": fees["snap_pays_fees"],
        "fees_not_covered": fees["fees_not_covered"],
        "fees_silent": fees["silent"],
        "points_to_official": sum(bool(it["code"].get("points_to_official")) for it in open_items),
    }


def check_rows(items: list[dict], adj: dict | None = None, city: bool = True) -> list[dict]:
    adj = adjudications() if adj is None else adj
    out = []
    for it in items:
        if it["framing"] != "check":
            continue
        truth = panel_truth(it["retailer"], it["state"])
        usda = usda_truth(it["retailer"], it["page"])
        verdict = it["code"].get("verdict")
        serves = city_serves(it["retailer"], it["place"]) if city else None
        truth_final = final_truth(truth, verdict, adj.get(it["id"]), serves)
        out.append({"run_id": it["id"], "place": it["place"], "page": it["page"], "retailer": it["retailer"],
                    "truth": truth, "usda": usda, "verdict": verdict, "outcome": outcome_for(verdict, truth),
                    "city_serves": serves, "truth_final": truth_final, "final": outcome_for(verdict, truth_final),
                    "confidence": policies()[it["retailer"]].get("confidence", "high")})
    return out


def check_measures(items: list[dict], headline: bool = True, field: str = "final", adj: dict | None = None,
                   city: bool = True) -> dict:
    """headline=True leaves out retailers whose answer key is low confidence (Gopuff: no published state list).
    field="final" uses the hand check; field="outcome" is the state-level key alone."""
    every = [r for r in check_rows(items, adj, city) if r[field] not in ("banner", "uncoded")
             and (not headline or r["confidence"] != "low")]
    rows = [r for r in every if r[field] != "unclear"]
    c = Counter(r[field] for r in rows)
    t = "truth_final" if field == "final" else "truth"
    truth_no = [r for r in rows if r[t] == "no"]
    truth_yes = [r for r in rows if r[t] == "yes"]
    n = len(rows)
    return {
        "questions": n, "unclear": len(every) - n,
        "correct": c["correct"], "false_yes": c["false_yes"], "false_no": c["false_no"], "hedged": c["hedged"],
        "accuracy": c["correct"] / n if n else None,
        # of the cases where the answer key says no, how often the assistant said yes anyway
        "false_yes_rate": sum(r[field] == "false_yes" for r in truth_no) / len(truth_no) if truth_no else None,
        "false_no_rate": sum(r[field] == "false_no" for r in truth_yes) / len(truth_yes) if truth_yes else None,
        # how often USDA's state page disagrees with the retailer's own policy (a finding about the list)
        "usda_disagrees": sum(r["usda"] != r["truth"] for r in rows),
    }


def by_retailer(items: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for it in items:
        if it["framing"] == "check":
            groups[it["retailer"]].append(it)
    return {k: check_measures(v, headline=False) for k, v in groups.items()}


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def main():
    items = joined(read_jsonl(RUNS), read_jsonl(CODES))
    DERIVED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    for name, rows in (("stores.csv", store_rows(items)), ("checks.csv", check_rows(items))):
        if rows:
            with (DERIVED / name).open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    o, k, raw = open_measures(items), check_measures(items), check_measures(items, field="outcome")
    mid = check_measures([it for it in items], field="final", city=False)
    adj = adjudications()
    open_adj = [a for a in adj.values() if ":check:" not in a["run_id"]]
    names = dict(PANEL)
    lines = ["# SNAP Online Check: results", "", f"Answers scored: {len(items)}", "",
             "## Open questions (where, nocar)", "",
             f"* Stores the assistant said take EBT online: {o['stores_endorsed']}",
             f"* ...wrong for the shopper: {o['endorsed_wrong']} ({pct(o['share_endorsed_wrong'])} of those that could "
             f"be checked); of these, {o['endorsed_wrong_city']} trade in the state but have no store serving the city",
             f"* ...city coverage unclear (left out): {o['endorsed_city_unclear']}",
             f"* ...not confirmed by the retailer table or the USDA page (hand-check sample): {o['endorsed_unverified']}",
             f"* Answers naming at least one wrong store: {o['answers_with_a_wrong_store']} of {o['answers']} "
             f"({pct(o['share_answers_with_wrong'])})",
             f"* Says SNAP can pay delivery or service fees: {o['fees_snap_pays']}; says it cannot: "
             f"{o['fees_not_covered']}; silent: {o['fees_silent']}",
             f"* Hand check of the wrong stores: {sum(a['assistant_right'] == 'no' for a in open_adj)} of {len(open_adj)} confirmed wrong",
             f"* Points to USDA, the state agency or the retailer to confirm: {o['points_to_official']}",
             f"* Parent-chain mentions where USDA lists a banner (not scored): {o['banner_mentions']}; "
             f"delivery-app mentions (not scored): {o['platform_mentions']}",
             "", "## Named-retailer questions (check)", "",
             f"* Questions scored: {k['questions']} (Gopuff left out: low-confidence answer key; {k['unclear']} left out as "
             f"unclear after the hand check); accuracy {pct(k['accuracy'])}",
             f"* Against the state-level key alone, before the hand check: {raw['questions']} scored, accuracy "
             f"{pct(raw['accuracy'])}, false yes {pct(raw['false_yes_rate'])}, false no {pct(raw['false_no_rate'])}",
             f"* False yes (said yes where the shopper's city has no store taking EBT online): {pct(k['false_yes_rate'])} ({k['false_yes']})",
             f"* False no (said no where the shopper's city does have one): {pct(k['false_no_rate'])} ({k['false_no']})",
             f"* Against the state key plus the hand check of disagreements only: accuracy {pct(mid['accuracy'])}, "
             f"false yes {pct(mid['false_yes_rate'])}",
             "* Final scores use the right answer for the shopper's city: the state key, the hand check of every "
             "disagreement, and a check of every yes against the retailer's store locator.",
             f"* Hedged with no bottom line: {k['hedged']}",
             f"* Questions where USDA's state page disagrees with the retailer's own policy: {k['usda_disagrees']}",
             "", "| Retailer | Scored | Accuracy | False yes | False no | Hedged |", "| --- | --- | --- | --- | --- | --- |"]
    for rk, m in sorted(by_retailer(items).items()):
        lines.append(f"| {names[rk]} | {m['questions']} | {pct(m['accuracy'])} | {pct(m['false_yes_rate'])} | "
                     f"{pct(m['false_no_rate'])} | {m['hedged']} |")
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
