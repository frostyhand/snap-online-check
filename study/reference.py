"""The answer key: which retailers USDA lists as taking SNAP online in each state, and name matching."""

import csv
import json
import re
from collections import defaultdict
from functools import lru_cache

from study.config import PANEL, REFERENCE

KEY_FILE = REFERENCE / "usda_snap_online.csv"

# Delivery apps that pass SNAP orders to stores. USDA lists stores, not apps, so a named app is reported
# but never scored right or wrong on its own.
PLATFORMS = {"instacart", "doordash", "uber eats", "ubereats", "shipt", "grubhub", "postmates", "favor"}

# Name variants a shopper or an assistant uses for the same USDA entry (normalized form on both sides).
ALIASES = {
    "amazon fresh": "amazon", "amazoncom": "amazon", "amazon prime": "amazon",
    "whole foods market": "whole foods",
    "go puff": "gopuff",
    "sprouts farmers": "sprouts",
    "hy vee": "hyvee",
    "bjs wholesale": "bjs", "bjs wholesale club": "bjs",
    "cvs pharmacy": "cvs",
    "doordash dashmart": "dashmart",
    "schnucks": "schnucks", "schnuck": "schnucks",
    "dierbergs": "dierbergs", "dierberg": "dierbergs",
    "commissary": "defense commissary agency", "deca": "defense commissary agency",
    "smiths": "smiths food and drug", "smiths food drug": "smiths food and drug", "smiths food and drug stores": "smiths food and drug",
    "giant food": "giant of maryland",
    "frys food": "frys", "frys food stores": "frys",
    "harris teeter": "harris teeter",
    "aldi us": "aldi",
    "h e b": "heb",
    "smiths food and drug": "smiths food and drug",
    "target circle": "target",
}

# Parent chains whose stores trade under other names in many states. If an answer names the parent and
# USDA lists only a banner in that state, the mention counts as "banner" (reported apart, not as wrong).
BANNERS = {
    "kroger": {"king soopers", "ralphs", "fred meyer", "frys", "smiths food and drug", "food 4 less", "qfc",
               "harris teeter", "marianos", "dillons", "pick n save", "metro", "ruler foods", "city",
               "bakers", "gerbes", "jay c", "pay less", "owens", "foods co"},
    "albertsons": {"safeway", "jewel osco", "acme", "shaws", "star", "tom thumb", "randalls", "vons",
                   "pavilions", "carrs", "haggen", "united supermarkets", "albertsons"},
    "safeway": {"albertsons", "vons", "carrs", "pavilions"},
}

_DROP = {"the", "inc", "llc", "co", "corp", "company", "market", "markets", "supermarket", "supermarkets",
         "store", "stores", "banners", "grocery"}


def norm(name: str) -> str:
    s = (name or "").lower().replace("’", "'").replace("&", " and ")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\bscan (and|n) go\b", " ", s)
    s = re.sub(r"https?://|www\.|\.com\b", " ", s)
    s = s.replace("'", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    words = [w for w in s.split() if w not in _DROP]
    s = " ".join(words)
    s = ALIASES.get(s, s)
    return s


@lru_cache(maxsize=1)
def answer_key() -> dict[str, set[str]]:
    """USDA page name -> set of normalized retailer names."""
    key: dict[str, set[str]] = defaultdict(set)
    with KEY_FILE.open() as fh:
        for row in csv.DictReader(fh):
            key[row["page"]].add(norm(row["retailer"]))
    for page, extra in INCLUDES.items():
        for e in extra:
            key[page] |= key[e]
    return dict(key)


# The New York City page lists only stores added for NYC (Key Food, C-Town, Foodtown...). Statewide
# retailers on the New York page (Amazon, Walmart, ShopRite...) also serve the city.
INCLUDES = {"New York City": ["New York"]}


@lru_cache(maxsize=1)
def captured() -> dict[str, str]:
    out = {}
    with KEY_FILE.open() as fh:
        for row in csv.DictReader(fh):
            out[row["page"]] = row["captured"]
    return out


def _listed(n: str, names: set[str]) -> bool:
    if n in names:
        return True
    # "jewel osco" vs "jewel osco pharmacy": accept when one name is the other plus extra words
    return any(len(n) >= 4 and (x.startswith(n + " ") or n.startswith(x + " ")) for x in names)


def status(name: str, page: str) -> str:
    """listed | banner | platform | not_listed, for a retailer named to a shopper on this USDA page."""
    n = norm(name)
    if not n:
        return "not_listed"
    if n in PLATFORMS or any(n.startswith(p + " ") for p in PLATFORMS):
        return "platform"
    names = answer_key()[page]
    if _listed(n, names):
        return "listed"
    if any(b in names for b in BANNERS.get(n, ())):
        return "banner"
    return "not_listed"


def usda_truth(retailer_key: str, page: str) -> str:
    """yes | banner | no: does USDA list this panel retailer as taking SNAP online on this page?
    A secondary measure only: the USDA pages are incomplete (Kroger, online-EBT companywide since 2023,
    is missing from the Texas page)."""
    name = dict(PANEL)[retailer_key]
    s = status(name, page)
    return {"listed": "yes", "banner": "banner"}.get(s, "no")


POLICIES_FILE = REFERENCE / "retailer_policies.json"


@lru_cache(maxsize=1)
def policies() -> dict:
    return json.loads(POLICIES_FILE.read_text())["retailers"]


def panel_truth(retailer_key: str, state: str) -> str:
    """yes | banner | no from the retailer's own SNAP policy and footprint (the primary answer key)."""
    p = policies()[retailer_key]
    if p.get("accepts_ebt_online") and state in p.get("states", []):
        return "yes"
    if state in p.get("banner_states", []):
        return "banner"
    return "no"


@lru_cache(maxsize=1)
def _panel_names() -> dict[str, str]:
    return {norm(name): key for key, name in PANEL} | {norm(p.get("name", "")): k for k, p in policies().items()}


def panel_key(name: str) -> str | None:
    return _panel_names().get(norm(name))


def verify(name: str, page: str, state: str) -> str:
    """Status of a store an open answer endorsed: ok (retailer policy says yes), wrong (retailer policy
    says no), banner, platform, usda_listed (not a panel retailer, but on the USDA page), or unverified
    (neither source confirms it; hand-checked on a sample)."""
    s = status(name, page)
    if s == "platform":
        return "platform"
    rk = panel_key(name)
    if rk:
        return {"yes": "ok", "banner": "banner", "no": "wrong"}[panel_truth(rk, state)]
    if s == "listed":
        return "usda_listed"
    if s == "banner":
        return "banner"
    return "unverified"


# Amazon ships SNAP-eligible groceries nationwide, so it serves every city in the study.
NATIONWIDE = {"amazon"}


@lru_cache
def city_coverage() -> dict[tuple[str, str], str]:
    """(retailer key, place) -> yes/no/unclear: does a store under the retailer's own name serve that city?
    Checked by hand against store locators (data/reference/city/<retailer>.csv)."""
    out = {}
    for p in sorted((REFERENCE / "city").glob("*.csv")):
        with p.open() as fh:
            for r in csv.DictReader(fh):
                out[(r["retailer"], r["place"])] = r["serves"]
    return out


def city_serves(retailer_key: str | None, place: str) -> str | None:
    if retailer_key in NATIONWIDE:
        return "yes"
    return city_coverage().get((retailer_key, place))
