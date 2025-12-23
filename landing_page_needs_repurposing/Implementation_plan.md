# ContinuuAI Landing Page – Implementation Plan

Purpose: repurpose this folder into a focused marketing/landing site for ContinuuAI (decision continuity, proactive dashboard, evidence-anchored assistant). Keep it fast, intentional, and aligned with the product we just shipped (decision streams, dashboard, insights).

## Positioning
- Promise: “ContinuuAI preserves decision reasoning, surfaces conflicts/drift, and keeps teams aligned without digging through chat.”
- Core value props: 30-second decision capture (“verify, don’t write”), dissent preserved and surfaced, pattern/conflict detection, successor briefings, proactive dashboard over chat.
- Primary CTA: “See the Decision Dashboard” (link to user-app `/dashboard` or a guided demo).
- Secondary CTA: “Record your first decision” (link to `/record`).

## Page Structure (single page, scroll)
1. **Hero** – headline + subhead, CTA buttons, background showing dashboard hero. Add quick stats badges (e.g., “Decisions revisited on time”, “Conflicts surfaced automatically”).
2. **Problem → Promise** – short copy: “Chat with docs is reactive; Continuity needs proactive mirrors.” Use bullets for pains: lost rationale, repeated mistakes, ignored dissent.
3. **How ContinuuAI Works** – 4 steps with icons:
   - Capture in 30s (pre-filled form, dissent preserved)
   - Organize into streams (projects/areas)
   - Surface patterns (drift/conflicts, revisit reminders)
   - Brief successors (context packages)
4. **Product Highlights** – cards/screenshots for:
   - Needs Attention panel (revisit due, unresolved dissent, insights)
   - Decision detail page (reasoning, constraints, dissent, uncertainty, outcomes)
   - Query/Ask Julian (evidence-anchored answers)
5. **Proof & Principles** – list the guardrails: evidence-anchored, non-directive, exit-safe, org-specific learning.
6. **Call to Action** – repeat CTA with small form (email/demo) + link to live dashboard route.
7. **FAQ** – short answers: data residency (local), models (Gemma via llama.cpp), how dissent is stored, how conflicts are detected (batch, deterministic first).

## Visual Direction
- Typography: purposeful display for headlines (e.g., Space Grotesk/Clash/Manrope), readable body.
- Color: keep brand gradient used in apps (blue-indigo) but add depth with layered shapes/glow; avoid generic purple-on-white.
- Layout: glass/blur accents sparingly; bold hero with product mock; staggered reveal for sections.
- Assets: reuse actual UI captures from `services/user-app` dashboard and decision detail.

## Build Approach
- Prefer React/Vite or Next.js static export; no backend required unless we embed live data.
- If embedding live: proxy to existing API/user-app; gate with mock data toggle.
- Keep Lighthouse-friendly: ship minimal JS for marketing sections, lazy-load heavy assets.

## Tasks
- [ ] Swap old NeuAIs copy with ContinuuAI messaging (Hero/Problem/How/Highlights/FAQ).
- [ ] Drop unused backend services or clearly mark them as archived (if we keep the folder).
- [ ] Add assets folder for dashboard/decision screenshots.
- [ ] Wire CTAs to live routes (`/dashboard`, `/record`) and optional “Book a demo” mailto/form.
- [ ] Add simple tailwind/vanilla CSS token set (colors, spacing, radii) matching product.
- [ ] Optional: add demo toggle to show mocked dashboard cards without requiring login.

## Deliverables
- Single-page marketing site ready to host statically.
- Copy deck grounded in the current strategic doc (“From Chat to Decision Continuity”).
- Updated README with quick start instructions for preview/build.
