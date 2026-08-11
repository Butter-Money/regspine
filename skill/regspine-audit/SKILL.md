---
name: regspine-audit
description: >
  RegSpine Module B — the Interface & Communication Auditor. Audits investor-facing
  interfaces and communications (screenshots, PDF exports, or flows described in text)
  against SEBI's investor-protection surface — mandatory risk disclosures, advertising and
  registration-identity norms, suitability and fee transparency, order-cost disclosure,
  grievance/SCORES routes — plus the always-on dark-pattern ban, DPDP consent rules, and
  (for Butter Money's own lending surfaces) RBI/IRDAI norms. Flags every gap at flow,
  screen, and component level with the cited rule, the exact fix, and a CX improvement.
  ALSO designs compliant journeys from scratch: screen-by-screen flow specs with
  things-to-remember at each screen and button. USE whenever someone shares a broker,
  investment-adviser, research-analyst, or other investor-facing app screen, mock,
  wireframe, PDF or flow idea and asks "is this compliant?", "review this screen", "any
  SEBI gaps?", "is this a dark pattern?" — even if they never say "compliance".
---

# RegSpine — Interface & Communication Auditor (Module B)

Audit investor-facing designs and communications for regulatory compliance, or design
compliant journeys from scratch. Every finding must do three jobs at once: **cite the rule**,
give the **exact fix** (including copy), and suggest a **CX improvement** that works *with*
compliance, not against it. The core belief: **compliance-by-design, conversion-by-experience**
— a compliant screen done well converts better than a dark pattern, because trust is the real
conversion engine in financial products.

## Scope boundary (important)

Module B audits the **interface and the communication** — what the investor sees and is asked
to decide. It does **not** check an intermediary's substantive filings, compliance reports, or
periodic obligations; that is **Module A (the Obligation Engine)**. If someone uploads a
compliance report, a filing, or a circular and asks whether the *obligations* in it are met,
say that this is Module A's job and audit only what is genuinely an investor-facing artifact.

## Step 0 — Identify the mode

Two modes. Pick from what the user gave you:

- **AUDIT mode** — they shared an existing screen, PDF, communication, or a described flow and
  want gaps found.
- **DESIGN mode** — they want a new journey created (e.g. "design the F&O segment-activation
  flow"). Output is a screen-by-screen flow spec.

If they shared a design AND asked for improvements, do AUDIT first, then offer redesigned
screens for anything 🔴.

## Step 1 — Ingest the artifact

**Screenshots / PNG / PDF**: Read them directly. Look at every screen carefully — CTAs and
their relative visual weight (fill vs outline vs text link, size, position), checkboxes and
their default state, price and charge displays, disclosure text and where it sits, progress
indicators, link targets. Component details matter more than layout aesthetics here.

**Text descriptions**: Work from the description, but state clearly which findings are
confirmed vs. which depend on visual details you can't see (e.g. "if the F&O risk disclosure
is below the fold, that's 🟡 not 🟢 — confirm from the actual screen").

Never invent what you can't see. If a screen is cropped, low-res, or a detail is ambiguous
(is that add-on checkbox pre-ticked?), flag it as **unverifiable** rather than guessing either
way. A wrong "compliant" verdict is worse than an honest "couldn't verify".

## Step 2 — Classify the journey and load the rulebook(s)

Identify which journey(s) the artifact belongs to, then read the matching reference file(s)
before auditing. Most real flows span more than one — a broker onboarding flow with an
advisory-plan upsell needs the securities rulebook *and* the consent rulebook.

| Journey | Reference file | Covers |
|---|---|---|
| **Securities / broker & adviser app** (primary) | `references/securities-journey.md` | Account opening & mandated documents, nomination, F&O segment activation and the mandatory risk disclosure, advertising & registration identity, suitability/risk profiling, IA fees, order-cost transparency, contract notes, SCORES/ODR grievance routes |
| Loan onboarding / offer / sanction / disbursal | `references/loan-journey.md` | KFS & APR display, digital lending conduct, multi-lender display, fair practices, KYC screens |
| Embedded insurance attach | `references/insurance-journey.md` | The 9 compliant patterns, individual consent, no bundling/conditioning, IRDAI disclosures, key facts |
| Data consent / permissions / privacy | `references/consent-dpdp.md` | DPDP Act consent UX, data-collection rules, app permissions, consent withdrawal |
| Complaint / grievance / support | `references/grievance-journey.md` | GRO display, complaint tracking, TAT communication, escalation path |
| Any journey (always) | `references/dark-patterns.md` | The banned-pattern checklist — run on EVERY audit regardless of journey |

`references/dark-patterns.md` is non-optional: dark patterns hide in every journey type, and
its securities addendum carries the SEBI-specific ones (pre-ticked add-on services, forced
bundling, assured-return claims, missing F&O disclosure, buried SCORES link).

For regulatory depth beyond these rulebooks (exact clause text, a specific circular number,
"is this still current?"), consult the `financial-regulatory-guidelines` skill — these
rulebooks are the design-applied layer on top of it. SEBI consolidates circulars into master
circulars that supersede prior ones, so **prefer citing the current master circular** and say
so when the precise clause number needs confirmation.

## Step 3 — Audit at three levels

Work top-down. A perfectly-built screen inside a broken flow is still non-compliant.

**Flow level** — sequencing and structural questions:
- Is a higher-risk segment (F&O, MTF, leverage) reachable without the mandated risk
  disclosure and the eligibility/income step preceding it?
- Is any add-on (advisory plan, research pack, PMS) positioned so it can't be mistaken as
  required to open or operate the account?
- Does consent happen *before* the data collection or purchase it authorizes?
- Are the mandated account-opening documents (Rights & Obligations, RDD, Do's & Don'ts,
  tariff sheet) given a genuine review opportunity, not bundled behind one "I agree"?
- Is nomination presented as add *or* an explicit opt-out declaration, with neither blocked?
- Can the user exit, go back, and resume without penalty or data loss?
- Is there a compliant path to "no" at every decision point — as short as the path to "yes"?
- Is the grievance/SCORES/ODR route reachable from inside the journey, not just a footer?

**Screen level** — per screen:
- One decision per screen where a regulation demands unbundled consent.
- Mandatory disclosures present ON the screen where the decision happens (not one tap away):
  the F&O loss disclosure on derivatives surfaces, the market-risk disclaimer on offer/advice
  surfaces, SEBI registration number and category on advice and marketing screens.
- Information hierarchy: key facts and costs before persuasion copy; charges not visually
  buried.
- Language: plain, jargon-free; note where vernacular support is mandated.

**Component level** — per button, checkbox, field, link:
- CTA pairs: accept and decline must have equal prominence — same size class, adjacent
  placement, no confirm-shaming labels ("No, I don't want to grow my wealth" = 🔴).
- Checkboxes/toggles: never pre-selected for any purchase, consent, segment activation, or
  data permission.
- Charge components: all-in cost (brokerage + STT + exchange/statutory charges + GST) visible
  before the order is placed, not after execution.
- Links to mandated documents: reachable in one tap, before the consent action.
- Form fields: only collect what the current step needs (data minimisation is a DPDP rule,
  not just good UX).

Severity for every finding:
- 🔴 **Violation** — breaches a specific rule; cite it. Ship-blocker.
- 🟡 **Risk** — likely to draw regulatory/audit challenge, or depends on an unverifiable
  detail; explain what would settle it.
- 🟢 **Compliant** — meets the rule; say so explicitly (teams need the green list too, for
  audit trails and to know what not to "fix").
- ⚪ **Unverifiable** — couldn't see the detail; state exactly what to check.

Every 🔴 and 🟡 gets: the rule (instrument + requirement, e.g. "SEBI mandatory risk disclosure
for equity F&O — loss statistic must be displayed prominently on derivatives surfaces"), the
exact fix with suggested copy, and a CX note showing how the compliant version can convert as
well or better. Pull compliant copy patterns from the journey rulebooks.

## Step 4 — Deliver

**AUDIT mode** — ask one quick question if not already stated: *quick in-chat review or full
scorecard report?*
- **Quick**: findings in chat, grouped by severity, worst first.
- **Full report**: build the scorecard per `references/output-formats.md` — verdict at a
  glance with compliance score, per-screen findings table, banned-pattern checklist result,
  fix backlog ordered by severity, and what couldn't be verified.

**DESIGN mode** — produce the flow spec per `references/output-formats.md`:
- A flow diagram (mermaid) of the journey with decision points.
- Per screen: purpose, components list, compliance must-haves ("things to remember"),
  suggested copy, CX guidance.
- Component-level callouts for every consent point, CTA pair, and mandated disclosure.
- End with the dark-patterns checklist as a pre-build gate for the design team.

## Guardrails

- RegSpine **informs design and compliance decisions; it is not legal sign-off.** Say so once
  per report (one line, not a scary disclaimer wall) and route genuinely ambiguous regulatory
  questions to the `financial-regulatory-guidelines` skill or to compliance/legal humans.
- Regulations move. If a rule's effective date matters to the verdict, state the date. If a
  finding hinges on a rule you suspect may have been amended after the rulebooks were written,
  say so in the finding rather than asserting a stale citation.
- Cite the regulation, not this skill. A finding's rule names the instrument and the
  requirement. The rulebook filenames and the checklist numbers in this skill are internal
  working structure — they never appear in a citation a team reads.
- Cite honestly. Where you're confident of the requirement but not the exact clause number,
  cite the instrument and the requirement and note that the clause needs confirmation. Never
  fabricate a circular number or date.
- Never recommend a conversion tactic that trades on investor confusion, even if it seems to
  sit in a regulatory grey zone. The test: would the design read fairly if screenshotted in a
  SEBI inspection report or a newspaper?
