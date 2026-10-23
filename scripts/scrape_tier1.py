#!/usr/bin/env python3
"""Scrape Tier 1 officials (current Rollingwood government) from rollingwoodtx.gov.

Dry-run by default — prints the full extracted roster for review. Use --write to
commit the result to prompts/roster/tier1_officials.yml.

Sources (CivicPlus CivicEngage site, migrated from Drupal mid-2026):
  - /m/directory                  (Council + all city staff, tagged by dept)
  - /290, /289, /288, /293, /287, /291 commission pages

--write replaces only jurisdiction=Rollingwood entries in the shared roster
file. Entries written by other scrapers (scrape_tml.py) are left untouched,
and aliases already on a Rollingwood entry (e.g. ones appended by
scrape_tier2.py) are carried forward onto the refreshed entry.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

BASE = "https://www.rollingwoodtx.gov"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    )
}
OUTPUT = (
    Path(__file__).parent.parent / "prompts" / "roster" / "tier1_officials.yml"
)

# Alias overrides — canonical_name -> list of variants to add. Captures
# transcript garbles we've seen plus obvious spelling variants.
ALIAS_MAP: dict[str, list[str]] = {
    "Gavin Massingill": ["Gavin Massengill", "Massengill", "Massingale", "Maske"],
    "Brook Brown": ["Brooke Brown", "Brooke"],
    "Kevin Glasheen": ["Kevin Glashen", "Glashen"],
    "Sara Hutson": ["Sarah Hutson", "Sara Hudson", "Sarah Hudson", "Hudson"],
    "Phil McDuffee": ["Phil McDuffie", "McDuffie"],
    "Amy Pattillo": ["Amy Petillo", "Amy Pitillo", "Amy Patillo",
                     "Petillo", "Pitillo", "Patillo"],
    "Thom Farrell": ["Tom Farrell"],
    "Brian Rider": ["Brian Ryder", "Ryder"],
    "Bobby Hempfling": ["Bobby Hempling", "Hempling"],
    "Alun Thomas": ["Alan Thomas", "Alan"],
    "Kristal Muñoz": ["Crystal Munoz", "Crystal Muñoz", "Kristal Munoz", "Munoz"],
    "Christopher Meakin": ["Christpher Meakin", "Chris Meakin"],  # pre-2026 site typo
    # Prior site spellings (renames seen in the 2026 CivicPlus migration).
    "Nikki Stautzenberger-Praker": ["Nikki Stautzenberger", "Stautzenberger"],
    "Donald Bowne": ["Don Bowne"],
    "Josh Mosely": ["Joshua Mosely"],
    "Ismael Parra": ["Izzy Parra", "Izzy"],
}

# Short abbreviation prepended to roles on commission pages so combined roles
# read cleanly (Dave Bench → "P&Z Chair; CRCR Chair").
BODY_ABBREV: dict[str, str] = {
    "Parks Commission": "Parks",
    "Planning & Zoning Commission": "P&Z",
    "RCDC": "RCDC",
    "Board of Adjustment": "BOA",
    "Utility Commission": "Utility Commission",
    "CRCR": "CRCR",
}

# Manual first/last overrides for names where the last-word-is-surname
# heuristic fails (Dutch/German/Irish prefix surnames, etc.).
SURNAME_OVERRIDES: dict[str, tuple[str, str]] = {
    "Jay Van Bavel": ("Jay", "Van Bavel"),
}

# Canonical names to drop from Tier 1 entirely (no longer serving, site stale).
# These may still appear in Tier 2 when we scrape historical minutes.
DROP_NAMES: frozenset = frozenset()

# The Comprehensive Plan Strike Force (/292) is not scraped: the city marks
# it inactive. Its former members live in tier4_learned.yml so spellings
# still resolve.

JURISDICTION = "Rollingwood"
CONFIDENCE = "rollingwood_official"

DIRECTORY_PATH = "/m/directory"
COMMISSION_PAGES: list[tuple[str, str]] = [
    ("/290/Park-Commission", "Parks Commission"),
    ("/289/Planningand-Zoning", "Planning & Zoning Commission"),
    ("/288/RollingwoodCommunity-Development-Corpora", "RCDC"),
    ("/293/Board-of-Adjustment", "Board of Adjustment"),
    ("/287/Utility-Commission", "Utility Commission"),
    ("/291/Comprehensive-Residential-Code-ReviewCom", "CRCR"),
]


@dataclass
class RawHit:
    name: str
    role_on_body: str
    body: str
    snippet: str
    source_url: str = ""


@dataclass
class Person:
    canonical_name: str
    first: str
    last: str
    roles: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    snippets: list[tuple[str, str]] = field(default_factory=list)  # (body, snippet)
    source_url: str = ""  # first page the person was seen on


def fetch(path: str) -> str:
    url = BASE + path if path.startswith("/") else path
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def _clean_name(raw: str) -> str:
    # Strip quoted middle names ("Izzy"), collapse whitespace.
    cleaned = re.sub(r'\s*"[^"]+"\s*', " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _split_name(name: str) -> tuple[str, str]:
    if name in SURNAME_OVERRIDES:
        return SURNAME_OVERRIDES[name]
    parts = name.split()
    if len(parts) == 1:
        return (parts[0], "")
    return (" ".join(parts[:-1]), parts[-1])


def parse_directory(html: str) -> list[RawHit]:
    """CivicEngage /m/directory: one <li> per person under #nav-people, with
    name in a.fw-bold, position in div.d-sm-block, department links in
    ul.departments."""
    soup = BeautifulSoup(html, "html.parser")
    hits: list[RawHit] = []
    pane = soup.select_one("#nav-people")
    if pane is None:
        return hits
    for li in pane.select("ul.list-group > li.list-group-item"):
        name_el = li.select_one("a.fw-bold")
        if not name_el:
            continue
        name = _clean_name(name_el.get_text(" ", strip=True))
        if not name or name.lower().startswith("vacant"):
            continue
        pos_el = li.select_one("div.d-sm-block")
        role = pos_el.get_text(" ", strip=True) if pos_el else ""
        depts = [a.get_text(" ", strip=True) for a in li.select("ul.departments a")]
        hits.append(RawHit(
            name=name, role_on_body=role,
            body=", ".join(depts) or "Directory", snippet=str(li),
        ))
    return hits


def _li_is_linklike(li) -> bool:
    """True if the li's content is primarily a single document-link anchor."""
    anchors = li.find_all("a")
    txt = li.get_text(" ", strip=True)
    if not anchors:
        return False
    # One anchor whose text matches nearly the whole li text = link-only item.
    if len(anchors) == 1 and anchors[0].get_text(" ", strip=True) == txt:
        return True
    return False


def parse_commission(html: str, body_name: str) -> list[RawHit]:
    """Parse a /bc-* page. Tries each h2/h3 whose text mentions 'member' (except
    'Membership' alone) and returns hits from the first header whose list
    actually contains people (not document links)."""
    soup = BeautifulSoup(html, "html.parser")
    abbrev = BODY_ABBREV.get(body_name, body_name)

    candidates = []
    for h in soup.find_all(["h2", "h3"]):
        text = (h.get_text(" ") or "").strip().lower()
        if "member" not in text:
            continue
        if text == "membership":  # too generic — often document section
            continue
        candidates.append(h)

    for header in candidates:
        ul = header.find_next("ul")
        if ul is None:
            continue
        hits: list[RawHit] = []
        for li in ul.find_all("li", recursive=False):
            if _li_is_linklike(li):
                continue
            txt = li.get_text(" ", strip=True)
            if not txt or len(txt) > 200:
                continue
            if "," in txt:
                head, tail = txt.split(",", 1)
                name = _clean_name(head)
                role_label = tail.strip()
            else:
                name = _clean_name(txt)
                role_label = "Member"
            if not name or name.lower().startswith("vacant"):
                continue
            combined_role = f"{abbrev} {role_label}".strip()
            hits.append(RawHit(
                name=name, role_on_body=combined_role,
                body=body_name, snippet=str(li),
            ))
        if hits:
            return hits
    return []


def assemble(hits: list[RawHit]) -> dict[str, Person]:
    people: dict[str, Person] = {}
    for h in hits:
        key = h.name
        if key in DROP_NAMES:
            continue
        if key not in people:
            first, last = _split_name(h.name)
            people[key] = Person(canonical_name=h.name, first=first, last=last,
                                 source_url=h.source_url)
        p = people[key]
        if h.role_on_body and h.role_on_body not in p.roles:
            p.roles.append(h.role_on_body)
        p.snippets.append((h.body, h.snippet))
    for canonical, person in people.items():
        person.aliases = ALIAS_MAP.get(canonical, [])
    return people


def collect_all() -> dict[str, Person]:
    all_hits: list[RawHit] = []
    dir_hits = parse_directory(fetch(DIRECTORY_PATH))
    if not dir_hits:
        raise SystemExit(f"❌ No people parsed from {DIRECTORY_PATH} — site layout changed?")
    for h in dir_hits:
        h.source_url = BASE + DIRECTORY_PATH
    all_hits.extend(dir_hits)
    for path, body in COMMISSION_PAGES:
        html = fetch(path)
        hits = parse_commission(html, body)
        if not hits:
            raise SystemExit(f"❌ No members parsed from {path} ({body}) — site layout changed?")
        for h in hits:
            h.source_url = BASE + path
        all_hits.extend(hits)
    return assemble(all_hits)


def render_review(people: dict[str, Person]) -> str:
    lines: list[str] = []
    lines.append(f"# {len(people)} unique Tier 1 officials extracted\n")
    for canonical in sorted(people.keys(), key=str.casefold):
        p = people[canonical]
        lines.append(f"--- {p.canonical_name} ---")
        lines.append(f"  role:    {'; '.join(p.roles) if p.roles else '(none)'}")
        lines.append(f"  aliases: {p.aliases if p.aliases else '[]'}")
        lines.append(f"  first/last: {p.first!r} / {p.last!r}")
        for body, snippet in p.snippets:
            snip = re.sub(r"\s+", " ", snippet).strip()
            if len(snip) > 400:
                snip = snip[:400] + "…"
            lines.append(f"  [{body}] {snip}")
        lines.append("")
    return "\n".join(lines)


def merge_into_roster(people: dict[str, Person], existing: list[dict]) -> list[dict]:
    """Replace jurisdiction=Rollingwood entries with the fresh scrape; keep
    every other entry as-is. Aliases already on the old Rollingwood entry
    (ALIAS_MAP or scrape_tier2.py additions) are unioned onto the new one."""
    old_aliases = {
        e["canonical_name"]: e.get("aliases") or []
        for e in existing if e.get("jurisdiction") == JURISDICTION
    }
    kept = [e for e in existing if e.get("jurisdiction") != JURISDICTION]
    today = date.today().isoformat()
    fresh = []
    for p in people.values():
        aliases = list(p.aliases)
        for a in old_aliases.get(p.canonical_name, []):
            if a not in aliases:
                aliases.append(a)
        fresh.append({
            "canonical_name": p.canonical_name,
            "first": p.first,
            "last": p.last,
            "aliases": aliases,
            "role": "; ".join(p.roles),
            "source": "tier1",
            "confidence": CONFIDENCE,
            "jurisdiction": JURISDICTION,
            "source_url": p.source_url,
            "scraped_at": today,
        })
    return sorted(kept + fresh, key=lambda e: e["canonical_name"].casefold())


def read_roster() -> tuple[str, list[dict]]:
    """Return (leading comment block, entries)."""
    text = OUTPUT.read_text()
    header_lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith("#") or (header_lines and not line.strip()):
            header_lines.append(line)
            if not line.strip():
                break
        else:
            break
    header = "".join(header_lines)
    return header, yaml.safe_load(text) or []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help=f"Write YAML to {OUTPUT.relative_to(Path.cwd())}.")
    args = ap.parse_args()

    people = collect_all()
    print(render_review(people))

    if args.write:
        header, existing = read_roster()
        merged = merge_into_roster(people, existing)
        OUTPUT.write_text(
            header + yaml.safe_dump(merged, sort_keys=False, allow_unicode=True, width=1000)
        )
        print(f"\n✅ Wrote {OUTPUT}")
    else:
        print("(dry-run; pass --write to commit to tier1_officials.yml)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
