# ContinuuAI Landing (needs repurposing)

This folder is a scratchpad for the new ContinuuAI marketing/landing site. It currently contains a legacy "Colab clone" scaffold; keep the layout but retheme the content to focus on decision continuity, proactive dashboards, and Julian as a decision partner.

## Goals for the repurpose
- Tell the story: 30-second decision capture, dissent preserved, contradiction/drift detection, dashboard over chat.
- Show the product: decision dashboard hero, needs-attention list, record decision flow, briefing for successors.
- Make conversion easy: clear CTA to "See dashboard demo" and "Record your first decision."
- Keep fast iteration: lightweight build, minimal dependencies, easy to preview locally.

## Structure (to keep/refine)
- `frontend/` — landing page code (React/Vite scaffold from the old project).
- `backend/` — not needed for launch; keep only if we embed demo APIs (otherwise archive).
- `containers/` — deployment boilerplate; keep trimmed for static hosting or containerized preview.
- `docs/` — use for copy deck, brand guidelines, and IA notes.

## Immediate cleanup done
- Removed nested git workspace and Rust `target/` build artifacts.
- Left the scaffold intact for reuse.

## Next actions (recommended)
1. Strip unused backend code if we stick to a static/Next.js site.
2. Replace homepage content with ContinuuAI messaging (see Implementation_plan.md).
3. Add a "live demo" embed hitting the existing user-app dashboard if feasible.
4. Wire CTA buttons to the primary user-app routes (`/dashboard`, `/record`).
