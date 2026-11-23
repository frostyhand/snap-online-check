"""Build the answer key from USDA FNS "Stores Accepting SNAP Online" state pages.

FNS blocks automated requests to www.fns.usda.gov (HTTP 403), so the pages come from the Internet
Archive. usda_snapshots.txt lists one capture per state page (page name, Wayback timestamp).

    python scripts/build_reference.py            # parse saved snapshots in data/reference/snapshots/
    python scripts/build_reference.py --fetch    # download the listed captures first

US government works are public domain; the saved pages are kept for reproducibility.
"""

import argparse
import csv
import html
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "data" / "reference"
SNAP_DIR = REF / "snapshots"
LIST = REF / "usda_snapshots.txt"
OUT = REF / "usda_snap_online.csv"
PAGE = "https://www.fns.usda.gov/snap/snap-online-retailers/{page}"
WAYBACK = "https://web.archive.org/web/{ts}id_/{url}"
MARKER = "Accepting SNAP Payments Online"


def captures() -> list[tuple[str, str]]:
    return [tuple(line.split()) for line in LIST.read_text().splitlines() if line.strip()]


def fetch(page: str, ts: str) -> None:
    url = WAYBACK.format(ts=ts, url=PAGE.format(page=page))
    req = urllib.request.Request(url, headers={"User-Agent": "snap-online-check (research; github.com/frostyhand)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    if body[:2] == b"\x1f\x8b":
        import gzip
        body = gzip.decompress(body)
    (SNAP_DIR / f"{page}.html").write_bytes(body)


def parse(text: str) -> list[str]:
    i = text.find(MARKER)
    if i < 0:
        raise ValueError("retailer list not found")
    block = text[i:text.find("Return to top", i)]
    items = re.findall(r"(?is)<li[^>]*>(.*?)</li>", block)
    names = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip() for x in items]
    return [n for n in names if n]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args(argv)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for page, ts in captures():
        f = SNAP_DIR / f"{page}.html"
        if a.fetch or not f.exists():
            fetch(page, ts)
            time.sleep(3)
        names = parse(f.read_text(encoding="utf-8", errors="ignore"))
        captured = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
        source = WAYBACK.format(ts=ts, url=PAGE.format(page=page)).replace("id_/", "/")
        for n in names:
            rows.append({"page": urllib.parse.unquote(page), "retailer": n, "captured": captured, "source": source})
        print(f"{urllib.parse.unquote(page):22s} {captured} {len(names)}")
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["page", "retailer", "captured", "source"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
