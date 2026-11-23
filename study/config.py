"""Fixed study design: places, retailer panel, framings, paths."""

from datetime import date as _date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
DERIVED = DATA / "derived"
REFERENCE = DATA / "reference"
RESULTS = ROOT / "results"
ENV_FILE = ROOT / ".env"
# Main Street Share uses the same free Gemini key; its .env is the fallback and its ledger counts too,
# because the free quota belongs to the key, not to a study.
SIBLING = ROOT.parent / "main-street-share"

WAVE = "2026-11"

# (key, city, state abbreviation, USDA page name). One major city per state and DC. New York has two USDA
# pages: "New York City" (run by NYC HRA) and "New York" (rest of the state), so it gets two places.
PLACES = [
    ("al", "Birmingham", "AL", "Alabama"),
    ("ak", "Anchorage", "AK", "Alaska"),
    ("az", "Phoenix", "AZ", "Arizona"),
    ("ar", "Little Rock", "AR", "Arkansas"),
    ("ca", "Los Angeles", "CA", "California"),
    ("co", "Denver", "CO", "Colorado"),
    ("ct", "Hartford", "CT", "Connecticut"),
    ("de", "Wilmington", "DE", "Delaware"),
    ("dc", "Washington", "DC", "District of Columbia"),
    ("fl", "Miami", "FL", "Florida"),
    ("ga", "Atlanta", "GA", "Georgia"),
    ("hi", "Honolulu", "HI", "Hawaii"),
    ("id", "Boise", "ID", "Idaho"),
    ("il", "Chicago", "IL", "Illinois"),
    ("in", "Indianapolis", "IN", "Indiana"),
    ("ia", "Des Moines", "IA", "Iowa"),
    ("ks", "Wichita", "KS", "Kansas"),
    ("ky", "Louisville", "KY", "Kentucky"),
    ("la", "New Orleans", "LA", "Louisiana"),
    ("me", "Portland", "ME", "Maine"),
    ("md", "Baltimore", "MD", "Maryland"),
    ("ma", "Boston", "MA", "Massachusetts"),
    ("mi", "Detroit", "MI", "Michigan"),
    ("mn", "Minneapolis", "MN", "Minnesota"),
    ("ms", "Jackson", "MS", "Mississippi"),
    ("mo", "St. Louis", "MO", "Missouri"),
    ("mt", "Billings", "MT", "Montana"),
    ("ne", "Omaha", "NE", "Nebraska"),
    ("nv", "Las Vegas", "NV", "Nevada"),
    ("nh", "Manchester", "NH", "New Hampshire"),
    ("nj", "Newark", "NJ", "New Jersey"),
    ("nm", "Albuquerque", "NM", "New Mexico"),
    ("nyc", "New York City", "NY", "New York City"),
    ("ny", "Buffalo", "NY", "New York"),
    ("nc", "Charlotte", "NC", "North Carolina"),
    ("nd", "Fargo", "ND", "North Dakota"),
    ("oh", "Columbus", "OH", "Ohio"),
    ("ok", "Oklahoma City", "OK", "Oklahoma"),
    ("or", "Portland", "OR", "Oregon"),
    ("pa", "Philadelphia", "PA", "Pennsylvania"),
    ("ri", "Providence", "RI", "Rhode Island"),
    ("sc", "Columbia", "SC", "South Carolina"),
    ("sd", "Sioux Falls", "SD", "South Dakota"),
    ("tn", "Nashville", "TN", "Tennessee"),
    ("tx", "Houston", "TX", "Texas"),
    ("ut", "Salt Lake City", "UT", "Utah"),
    ("vt", "Burlington", "VT", "Vermont"),
    ("va", "Richmond", "VA", "Virginia"),
    ("wa", "Seattle", "WA", "Washington"),
    ("wv", "Charleston", "WV", "West Virginia"),
    ("wi", "Milwaukee", "WI", "Wisconsin"),
    ("wy", "Cheyenne", "WY", "Wyoming"),
]

# Retailers asked about by name in every place. Chosen because USDA lists some of them in some states and
# not in others, so a correct answer depends on where the shopper lives. (key, name as a shopper types it)
PANEL = [
    ("walmart", "Walmart"),
    ("amazon", "Amazon"),
    ("aldi", "ALDI"),
    ("costco", "Costco"),
    ("whole_foods", "Whole Foods"),
    ("kroger", "Kroger"),
    ("safeway", "Safeway"),
    ("publix", "Publix"),
    ("sprouts", "Sprouts"),
    ("gopuff", "Gopuff"),
]

FRAMINGS = {
    # Open questions: the assistant names the stores.
    "where": "I get SNAP and want to order groceries online with my EBT card. I live in {place}. "
             "Which stores can I use?",
    "nocar": "I'm on SNAP and don't have a car. I live in {place}. What's the cheapest way to get groceries "
             "delivered and pay with my EBT card?",
    # Closed question per panel retailer: yes or no has a right answer.
    "check": "Can I pay with my SNAP EBT card for an online grocery order from {retailer}? I live in {place}.",
}

SYSTEM = "Today is {date}. The user is in {city}, {state}, United States."


def place_label(p: tuple) -> str:
    return f"{p[1]}, {p[2]}"


def today_text(d: _date | None = None) -> str:
    d = d or _date.today()
    return f"{d:%A}, {d.day} {d:%B %Y}"


def prompts(wave: str = WAVE, day: str | None = None) -> list[dict]:
    day = day or today_text()
    out = []
    for key, city, st, page in PLACES:
        base = {"wave": wave, "place": key, "city": city, "state": st, "page": page,
                "system": SYSTEM.format(date=day, city=city, state=st)}
        where = place_label((key, city, st))
        for fk in ("where", "nocar"):
            out.append({**base, "id": f"{wave}:{key}:{fk}", "framing": fk, "retailer": None,
                        "prompt": FRAMINGS[fk].format(place=where)})
        for rk, name in PANEL:
            out.append({**base, "id": f"{wave}:{key}:check:{rk}", "framing": "check", "retailer": rk,
                        "prompt": FRAMINGS["check"].format(retailer=name, place=where)})
    return out
