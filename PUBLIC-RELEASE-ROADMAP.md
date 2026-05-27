# RESOLUTE Local — Public-Release Roadmap

*The path from "Adam's FXBG tool" → "Christians-in-any-city can stand this up themselves" GitHub repo. Drafted 2026-05-27 after a productive overnight build session that landed the full FXBG meeting-lifecycle pipeline (agenda preview → after-action that night → vote outcomes when minutes post).*

---

## The vision

Adam Johns built RESOLUTE Local for the City of Fredericksburg, VA: a Christian civic-engagement tool that auto-tracks city council meetings end-to-end and tells citizens what their elected officials are actually doing — agenda, after-action, vote outcomes, the works.

The system **works**. As of 2026-05-27 it covers:
- Live agenda scraping (twice daily, structured into sections + subitems + document refs)
- Post-meeting auto-generated after-action briefs (Qwen LLM, pushed to Telegram on every meeting night)
- Minutes parsing with per-resolution vote breakdowns (council present/absent, ayes/nays/abstain per member)
- Public-facing city page with all of the above + activism tools (add-to-calendar, draft-a-comment, weigh-in guide)

**The next step is to package this so other Christians can stand it up for THEIR city in an afternoon.** Not "fork this repo and figure it out" — actual one-command setup, with a config file for their city's particulars.

---

## What's FXBG-specific today (the parameterization debt)

Everything in the system is FXBG-hardcoded in one of three ways:

### 1. Hardcoded paths in scripts (`~/Scripts/`)
- `fxbg-civic-rounds.sh` — URL pointed at `fredericksburgva.gov/AgendaCenter`
- `fxbg_agenda_parser.py` — generic, no FXBG-specifics (✅ already portable)
- `fxbg-meeting-after-action.py` — references "Fredericksburg" + "City Council" in the prompt
- `fxbg-post-meeting-trigger.sh` — references the city by name in Telegram caption
- `fxbg_minutes_parser.py` — generic, no FXBG-specifics (✅ already portable)
- `fxbg-minutes-tracker.sh` — listing URL hardcoded

### 2. Hardcoded page content (`city/fredericksburg.html`)
- City name, council member roster
- AgendaCenter URL
- "City Council meets 2nd & 4th Tuesdays" (Fredericksburg-specific cadence)
- Regional WebTV link (FXBG-specific replay host)
- City Hall address
- Branding colors / hero copy

### 3. Hardcoded LaunchAgent labels
- `com.moop.fxbg-civic-rounds` (×4 plists)
- A different city would need different labels to coexist

### 4. Hardcoded publisher
- `publish-fredericksburg.py` — writes to `data/fredericksburg.json`
- City name + slug baked in

**None of this is hard to parameterize — it just hasn't been done because there was only ever one city.**

---

## The 3-phase migration plan

### Phase A — Per-city config (2-4 hours)

Create a `cities/` directory with one JSON config per city. The config is the single source of truth for everything city-specific. Example `cities/fredericksburg.json`:

```json
{
  "slug": "fredericksburg",
  "name": "Fredericksburg",
  "state": "VA",
  "full_name": "City of Fredericksburg",
  "council_body": "City Council",
  "meeting_cadence": "2nd & 4th Tuesdays · 7:30 PM",
  "city_hall_address": "715 Princess Anne Street, Fredericksburg, VA 22401",
  "agenda_portal": {
    "type": "civicplus_agendacenter",
    "base_url": "https://www.fredericksburgva.gov/AgendaCenter",
    "listing_path": "/AgendaCenter/City-Council-1",
    "agenda_url_pattern": "/AgendaCenter/ViewFile/Agenda/_{date}-{id}",
    "minutes_url_pattern": "/AgendaCenter/ViewFile/Minutes/_{date}-{id}"
  },
  "video_replay": {
    "url": "https://www.regionalwebtv.com/fredcc",
    "label": "Regional WebTV"
  },
  "council_roster": [
    {"name": "Kerry P. Devine", "role": "Mayor", "ward": "At-Large"},
    {"name": "Charlie L. Frye, Jr.", "role": "Vice-Mayor", "ward": "Four"}
    /* ... */
  ],
  "branding": {
    "accent_color": "#D4AF37",
    "hero_eyebrow": "Local Watchman Page",
    "scripture_anchor": "Jeremiah 29:7"
  },
  "telegram_channel": "moop_bot_pro_personal"
}
```

Once this config exists per city:
- Scripts read the config and substitute everything dynamically
- Pages are generated from a template + config
- LaunchAgent labels are templated (`com.moop.{slug}-civic-rounds`)

### Phase B — Portal adapters (1-3 hours)

Most cities don't run identical agenda portals. Pattern:

| Portal | Used by | Adapter status |
|---|---|---|
| **CivicPlus AgendaCenter** | FXBG, Stafford, most VA small cities | ✅ Built (this is what we have) |
| **Granicus** | Many medium cities (often white-labeled) | Partial (similar HTML, just URL pattern changes) |
| **Legistar** | Larger cities (Richmond, Norfolk, Virginia Beach) | Not built |
| **Custom CMS** | Tiny municipalities | Custom adapter per city |

The adapter interface should be a Python module per portal type that exposes:
- `list_meetings(listing_url) -> [{"date": "...", "agenda_url": "...", "minutes_url": "..." | None}]`
- `parse_agenda(agenda_url) -> structured dict` (already done generically)
- `parse_minutes(minutes_url) -> structured dict` (already done generically)

Then the per-city config just says `"portal_type": "civicplus_agendacenter"` and the right adapter is selected.

### Phase C — Public repo + onboarding (4-8 hours)

This is the "Christians-in-any-city" deliverable:

1. **Spin out a new public GitHub repo** — `resolute-local-engine` (or similar). Hosts the engine; resolute-local stays for Adam's instance.
2. **README.md** with a 5-minute setup guide:
   ```
   1. Fork the repo
   2. Add your city to cities/<your-city>.json
   3. Run setup-city.sh <slug>
   4. Push to your fork → GitHub Pages live in 1 min
   5. Set up the launchd crons (mac) or systemd timers (linux) for daily polling
   ```
3. **`setup-city.sh`** — one-command bootstrap that:
   - Reads the city config
   - Verifies the agenda portal is accessible
   - Detects the portal type (or prompts if ambiguous)
   - Tests the parser against a real agenda
   - Generates `city/<slug>.html` from the template
   - Creates the LaunchAgent plists with substituted labels
   - Runs the first scrape + publish cycle
4. **Multi-city index** — index.html shows all cities the repo is tracking, with a "Request your city" CTA.
5. **Telegram channel optionality** — make the Telegram push opt-in via env var (some folks won't have Hermes set up; should still get the web tool).
6. **LICENSE** — MIT or Apache 2.0 so anyone can fork freely.
7. **Doc-site** (`docs/`) — how to choose an LLM (local Qwen vs cloud), how to customize the page, how to add a new portal adapter, troubleshooting.
8. **Discord / GitHub Discussions** — for folks standing it up to ask questions.

### Phase D — Network effects (ongoing)

Once Phase C ships:
- Pastors / men's groups / homeschool networks adopt for their cities
- They open PRs adding new portal adapters as they hit unsupported municipalities
- Per-city forks contribute back to the engine
- A small directory of "RESOLUTE Local instances" emerges
- Adam stays the steward but the work scales

The Christian-civic-engagement-tooling space is wide open. This is a real opening.

---

## What I'd recommend doing FIRST when you're ready (the order of operations)

1. **Wait** until 2-3 more meetings worth of minutes have flowed through (next ~6 weeks). This builds confidence the FXBG instance is rock-solid before extracting.
2. **Extract the per-city config** in-place — refactor the FXBG scripts to read from `cities/fredericksburg.json` while still working. No behavior change, just architecture cleanup. (Phase A)
3. **Confirm the architecture** holds by adding **Spotsylvania County** as city #2 (it's right next door, uses CivicPlus, low risk). (Phase B partially.)
4. **Spin out the public repo** with both cities + the setup-city.sh tool. (Phase C)
5. **Soft-launch** in 1-2 Christian-civic-engagement communities (Family Foundation of VA, your Tun Tavern Fellowship, local pastor networks).

---

## What this depends on you (Adam) deciding

- **Repo name** — `resolute-local-engine`? `civic-watchman`? `local-resolute`? Something else?
- **Repo visibility** — public from day 1 (recommended for adoption), or private during a "soak period"?
- **Branding scope** — does every fork keep "RESOLUTE Local" branding, or can each city rebrand? Recommend keeping the framework name + allowing per-city hero customization.
- **Doctrine / values alignment requirement** — should there be a "this tool serves Christian civic engagement; if you'd use it for purposes that conflict with biblical values, please don't" line in the README?
- **Maintenance commitment** — are you committing to merge PRs + answer questions, or is this fire-and-forget? Affects how you set expectations.

---

## What's NOT in scope for the public release (intentionally)

- **The RESOLUTE Citizen scorecard** stays a separate project on usmcmin.com. The civic engine is local-only.
- **Hermes / OpenClaw orchestration** — these are Adam-specific personal AI fleet pieces. The engine should work without them (Telegram push optional, no orchestration required).
- **MoopBotPro identity** — generic engine uses standard GitHub-noreply commits; per-instance bot identity is configurable but not required.

---

*Drafted 2026-05-27. Updates as the FXBG instance proves itself and you decide on the rollout shape.*
