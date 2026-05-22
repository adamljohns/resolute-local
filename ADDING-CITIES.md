# Adding a City to RESOLUTE Local

RESOLUTE Local is built **multi-municipality from day one** — Fredericksburg is city #1,
the structure generalizes to any locality in the Commonwealth (and beyond). This is the
playbook for adding the next one.

## The per-city contract
Each city needs four things, all mirroring the Fredericksburg setup:

| Piece | Fredericksburg example | What it does |
|---|---|---|
| **Scraper** | `~/Scripts/fxbg-civic-rounds.sh` (cron `com.moop.fxbg-civic-rounds`) | Pulls the city's public agenda center → snapshot JSON in shared-memory |
| **Publisher** | `publish-fredericksburg.py` | Transforms the snapshot → `data/<city>.json` (council, next meeting, agenda items) |
| **Briefs** | `generate-briefs.py` + `briefs/<city>.json` | Local-LLM citizen briefs per meeting |
| **Page** | `city/fredericksburg.html` | Renders the live data + briefs + activism tools |

`~/Scripts/resolute-local-publish.sh` runs the brief + publish + git push (the live
self-update). The same wrapper can loop over multiple cities.

## Steps to add a city (e.g., Spotsylvania, Stafford, Richmond)
1. **Find the agenda source.** Most VA localities run a Granicus/CivicPlus "AgendaCenter"
   (same HTML pattern Fredericksburg uses) or a Legistar portal. Confirm the URL pattern.
2. **Clone the scraper.** Copy `fxbg-civic-rounds.sh` → `<city>-civic-rounds.sh`, point it
   at that city's agenda center, write to `shared-memory/context/<city>-civic-latest.json`.
   Add a cron (`com.moop.<city>-civic-rounds`).
3. **Clone the publisher.** Copy `publish-fredericksburg.py` → `publish-<city>.py`. The
   transform (council roster + next-meeting parse) is mostly reusable; tweak regexes for
   that city's agenda format.
4. **Clone the page.** Copy `city/fredericksburg.html` → `city/<city>.html`. Change the
   fetch path to `../data/<city>.json`, update the hero copy + city name. The live-render,
   brief block, calendar, and comment helper are city-agnostic — they just read the JSON.
5. **Add a card** to `index.html`'s city directory.
6. **Wire the publish wrapper** to run the new publish + briefs (one shared push).

## Scaling beyond hand-cloning
Once 3-4 cities exist, factor the page into a **single template + per-city config**
(`cities/<city>.json` with name, agenda URL, hero copy) and generate `city/<city>.html`
from it — like the scorecard's `generate-profiles.py`. Then adding a city = one config
entry + confirming the scraper pattern.

Two agenda-portal adapters cover most of Virginia:
- **CivicPlus / Granicus "AgendaCenter"** (Fredericksburg pattern) — done.
- **Legistar** (`<city>.legistar.com`) — common in larger cities; one adapter, many cities.

## "Request your city" intake
The Council-Notes page already has a *"Want Council Watch in your city?"* form. Route
submissions to a queue; each request = a candidate city to stand up via the steps above.
This is the **expansion path for others to use it** — demand-driven rollout.

## Data-quality rules (same as the scorecard)
- Source only from **official government agenda portals** — cite the source on every page.
- Council rosters parsed from the agenda header; verify against the city's official roster.
- Briefs are LLM-generated from the agenda; **factual, non-partisan, values-aware**, and
  never assert beyond what the agenda says. Manual briefs override auto ones.
