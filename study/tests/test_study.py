from study.config import FRAMINGS, PANEL, PLACES, prompts
from study.extract import build
from study.gemini import LEDGERS
from study.reference import answer_key, captured, norm, panel_truth, policies, status, usda_truth, verify
from study.score import check_measures, open_measures


def test_design_size_and_unique_ids():
    ps = prompts()
    assert len(PLACES) == 52
    assert len(ps) == len(PLACES) * (2 + len(PANEL)) == 624
    assert len({p["id"] for p in ps}) == len(ps)


def test_prompts_never_name_an_app_or_the_usda_list():
    for p in prompts():
        low = p["prompt"].lower()
        assert "instacart" not in low and "usda" not in low and "fns" not in low


def test_every_place_has_an_answer_key():
    key, when = answer_key(), captured()
    for _, _, _, page in PLACES:
        assert len(key[page]) >= 10, page
        assert when[page] >= "2025-12-01", page


def test_norm():
    assert norm("Sam’s Club Scan and Go") == "sams club"
    assert norm("Go-Puff") == norm("Gopuff") == "gopuff"
    assert norm("Whole Foods Market") == "whole foods"
    assert norm("H-E-B") == norm("HEB") == "heb"
    assert norm("Food 4 Less (Kroger)") == "food 4 less"
    assert norm("Stop & Shop") == "stop and shop"


def test_status_against_real_pages():
    assert status("H-E-B", "Texas") == "listed"
    assert status("Kroger", "Illinois") == "listed"
    assert status("Kroger", "Colorado") == "banner"          # King Soopers is listed
    assert status("King Soopers", "Colorado") == "listed"
    assert status("Instacart", "Texas") == "platform"
    assert status("Trader Joe's", "California") == "not_listed"
    assert status("Jewel-Osco", "Illinois") == "listed"


def test_nyc_includes_statewide_list():
    assert status("Key Food", "New York City") == "listed"
    assert status("Amazon", "New York City") == "listed"
    assert status("Key Food", "New York") == "not_listed"


def test_policies_cover_panel_with_sources():
    p = policies()
    for rk, _ in PANEL:
        assert rk in p and p[rk]["sources"] and p[rk]["confidence"] in ("high", "medium", "low"), rk


def test_panel_truth_from_retailer_policy():
    assert panel_truth("publix", "FL") == "yes"
    assert panel_truth("publix", "OR") == "no"
    assert panel_truth("kroger", "TX") == "yes"       # retailer policy, although USDA's Texas page omits it
    assert usda_truth("kroger", "Texas") == "no"
    assert panel_truth("kroger", "CO") == "banner"    # King Soopers
    assert panel_truth("walmart", "DC") == "yes"


def test_verify_open_answer_stores():
    assert verify("Kroger", "Texas", "TX") == "ok"
    assert verify("Publix", "Oregon", "OR") == "wrong"
    assert verify("Instacart", "Texas", "TX") == "platform"
    assert verify("H-E-B", "Texas", "TX") == "usda_listed"
    assert verify("Trader Joe's", "California", "CA") == "unverified"


def test_ledger_counts_main_street_share_too():
    assert any("main-street-share" in str(p) for p in LEDGERS)


ABBR = {page: st for _, _, st, page in PLACES}


def _item(framing, page, code, retailer=None, rid="x"):
    return {"id": rid, "place": "p", "page": page, "state": ABBR[page], "framing": framing,
            "retailer": retailer, "code": code}


def test_open_measures():
    items = [_item("where", "Texas", {"stores": [
        {"name": "H-E-B", "order": 1, "said_takes_ebt_online": "yes"},
        {"name": "Publix", "order": 2, "said_takes_ebt_online": "yes"},
        {"name": "Instacart", "order": 3, "said_takes_ebt_online": "yes"},
        {"name": "Joe's Corner Shop", "order": 4, "said_takes_ebt_online": "yes"}],
        "verdict": "not_applicable", "fees": "snap_pays_fees", "points_to_official": False})]
    m = open_measures(items)
    assert m["stores_endorsed"] == 3 and m["endorsed_wrong"] == 1 and m["endorsed_unverified"] == 1
    assert m["share_endorsed_wrong"] == 0.5 and m["platform_mentions"] == 1
    assert m["fees_snap_pays"] == 1


def test_check_measures():
    c = {"stores": [], "fees": "silent", "points_to_official": True}
    items = [
        _item("check", "Oregon", {**c, "verdict": "yes"}, "publix", "a"),    # false yes
        _item("check", "Florida", {**c, "verdict": "yes"}, "publix", "b"),   # correct
        _item("check", "Florida", {**c, "verdict": "depends"}, "publix", "c"),
        _item("check", "Colorado", {**c, "verdict": "yes"}, "kroger", "d"),  # banner, not scored
        _item("check", "Texas", {**c, "verdict": "yes"}, "kroger", "e"),     # correct, USDA disagrees
        _item("check", "Texas", {**c, "verdict": "no"}, "gopuff", "f"),      # low confidence, not headline
    ]
    m = check_measures(items)
    assert m["questions"] == 4 and m["correct"] == 2 and m["false_yes"] == 1 and m["hedged"] == 1
    assert m["false_yes_rate"] == 1.0 and m["usda_disagrees"] == 1
    assert check_measures(items, headline=False)["questions"] == 5


def test_extract_prompt_mentions_retailer_only_for_checks():
    run = {"city": "Houston", "state": "TX", "prompt": "q", "text": "t", "framing": "check"}
    assert "Publix" in build(run, "Publix")
    assert "not_applicable" in build({**run, "framing": "where"}, None)
    assert set(FRAMINGS) == {"where", "nocar", "check"}


def test_hand_check_overrides_the_state_level_key():
    c = {"stores": [], "fees": "silent", "points_to_official": False}
    items = [
        _item("check", "California", {**c, "verdict": "no"}, "safeway", "la"),   # no Safeway in LA: right
        _item("check", "Oregon", {**c, "verdict": "yes"}, "sprouts", "pdx"),     # no Sprouts in Oregon: wrong
        _item("check", "Delaware", {**c, "verdict": "yes"}, "whole_foods", "de"),  # cross-border: unclear
    ]
    adj = {"la": {"assistant_right": "yes"}, "pdx": {"assistant_right": "no"}, "de": {"assistant_right": "unclear"}}
    m = check_measures(items, adj=adj)
    assert m["questions"] == 2 and m["unclear"] == 1 and m["correct"] == 1 and m["false_yes"] == 1
    raw = check_measures(items, field="outcome", adj=adj)
    assert raw["questions"] == 3 and raw["correct"] == 0


def test_city_layer_turns_a_state_yes_into_a_city_false_yes(monkeypatch):
    import study.score as sc
    serves = {("safeway", "boise"): "no", ("whole_foods", "boise"): "unclear"}
    monkeypatch.setattr(sc, "city_serves", lambda rk, place: serves.get((rk, place), "yes"))
    c = {"stores": [], "fees": "silent", "points_to_official": False}
    items = [{**_item("check", "Idaho", {**c, "verdict": "yes"}, "safeway", "s1"), "place": "boise"},
             {**_item("check", "Idaho", {**c, "verdict": "yes"}, "whole_foods", "s2"), "place": "boise"},
             {**_item("check", "Idaho", {**c, "verdict": "yes"}, "walmart", "s3"), "place": "boise"}]
    m = sc.check_measures(items, adj={})
    assert m["questions"] == 2 and m["unclear"] == 1 and m["false_yes"] == 1 and m["correct"] == 1 and m["false_yes_rate"] == 1.0
    assert sc.check_measures(items, adj={}, city=False)["false_yes"] == 0
