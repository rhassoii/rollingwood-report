"""Roster lookup regression checks against the committed roster YAMLs.

Run: .venv/bin/python tests/test_roster.py   (also collects under pytest)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import roster  # noqa: E402

# Transcript spelling -> expected canonical name.
RESOLVES = {
    "Vaughn": "James Vaughan",       # phonetic, adjacent-body official
    "Speital": "Gerald Speitel",     # phonetic
    "Reiter": "Brian Rider",         # phonetic via "Ryder" alias (ratio 55)
    "Delcambre": "Barry Delcambre",  # exact surname, Tier 2
    "Brad Walters": "Brad Walters",  # exact, Tier 1
    "Zech": "Charles Zech",          # exact surname, Tier 2
    "Pat Barnes": "Patricia Barnes", # manual alias
}

# Bare first names whose Double Metaphone code collides with an unrelated
# surname. These must not resolve to that stranger.
MUST_NOT_RESOLVE_TO = {
    "Veronica": "Steve Franke",      # both FRNK
    "Patricia": "Edward Peters",
    "Phil": "James M Wiley",
}


def test_known_variants_resolve():
    for query, expected in RESOLVES.items():
        assert roster.lookup(query) == expected, (query, roster.lookup(query))


def test_phonetic_collisions_rejected():
    for query, wrong in MUST_NOT_RESOLVE_TO.items():
        assert roster.lookup(query) != wrong, (query, roster.lookup(query))


if __name__ == "__main__":
    test_known_variants_resolve()
    test_phonetic_collisions_rejected()
    print("ok")
