# ContinuuAI Landing

Lightweight marketing site focused on decision continuity, proactive dashboards, and Julian as a decision partner.

## What’s here
- `index.html` & `styles.css` — single-page static site (hero, problem, how-it-works, highlights, principles, CTA, FAQ).
- `Implementation_plan.md` — IA/copy plan for future edits.

## Preview locally
```bash
cd landing_page_needs_repurposing
python -m http.server 4000
# open http://localhost:4000
```

## Goals
- Tell the story: 30-second decision capture, dissent preserved, contradiction/drift detection, dashboard over chat.
- Show the product: decision dashboard hero, needs-attention list, record flow, successor briefing.
- Make conversion easy: CTA to “See dashboard demo” and “Record your first decision.”

## Next steps
- Replace mock blocks with real captures from the user app (dashboard, decision detail, Ask Julian).
- Add analytics/snippets if needed.
- If dynamic data is desired, embed API calls to `/dashboard` with a mock toggle.
