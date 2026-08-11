# Embedded Insurance Journey — rulebook + the 9 compliant patterns

Sources: Symbo "9 Patterns to Audit Before July 1" hack sheet (screen-by-screen playbook for
RBI NBFC Responsible Business Conduct Amendment Directions, 2026 — effective 01-Jul-2026);
IRDAI disclosure norms; RBI KFS circular. The 9 patterns below are both the audit criteria
(does the design do this?) and the design-mode building blocks.

## Non-negotiables on every insurance screen

1. "Insurance is optional and does not impact your loan approval" — visible, verbatim or
   equivalent, on every screen where insurance is offered or consented to.
2. Individual consent per insurance product, each with its own T&C access.
3. Insurer identity on the offer screen: name, logo, IRDAI registration number (CIN where
   space allows).
4. A decline path ("Continue Without Insurance") of equal prominence that completes the
   journey with no extra friction.
5. Premium shown as total (incl. taxes) wherever any framed price (per-day) appears.

## The 9 patterns (audit criteria ↔ design blocks)

### 1. The Loan Approval Moment
Offer protection immediately after loan approval, before disbursal confirmation — highest
intent point. ❌ Legacy: insurance buried as a checklist item ("Insurance (optional)") in a
process list. ✅ Approval banner → protection card (benefits, premium, insurer) → equal CTAs.
**Copy**: "Your ₹X loan is approved. Now protect the repayment risk." + "Insurance is optional
and does not impact loan approval."
*Design-mode note*: this placement is compliant BECAUSE approval is already communicated —
never show the offer before the approval verdict, which would imply conditioning.

### 2. Single Decision Offer Screen
One product, one premium, one insurer, one choice per screen. ❌ Multi-product checkbox
bazaars (loan protection + health + accident + travel + device on one screen) — cognitive
overload and a bundling-consent risk. ✅ The single most relevant product for the context.
Other products, if any, go to separate subsequent screens each with their own consent.

### 3. Value in Numbers, Not Claims
Show cover amount, one-time premium, daily-cost equivalent, and net disbursal on one card.
❌ Premium-only display with vague benefit prose. ✅ "Protect ₹1,00,000 for just ₹3.28 per
day" + one-time premium ₹1,200 + net disbursal figure. Total must be as findable as the
daily framing. "One-time payment. No hidden charges." only if literally true per the KFS.

### 4. Basic vs Plus vs No Thanks
Three-option choice architecture: Basic / Plus (may carry a RECOMMENDED badge) / No
Protection (₹0/day, phrased neutrally: "I'll manage the repayment risk independently").
❌ Binary yes/no pressure framing. ✅ No pre-selection, explicit opt-in, ₹0 option styled
identically to paid tiers. Footer: "Insurance is optional and does not impact loan approval."

### 5. Suitability into Personalization
Replace dead compliance checkboxes ("I confirm the product is suitable for me") with 2
diagnostic questions (dependents on income? existing cover for this loan?) that generate a
stated-basis recommendation: "Based on your answers, this loan currently has no repayment
protection." Recommendation basis shown = suitability documented = compliance artifact AND
better CX. Both CTAs still required: View Recommended Plan / Continue Without Protection.

### 6. Trust-Led Insurer Credibility
Use mandatory IRDAI disclosures as conversion assets: insurer name + logo, IRDAI regn. no.,
CIN, claims-settlement ratio with year ("99.5% claims settled in FY24"), settlement TAT
("most claims settled within 48 hours"), 4-step claims process strip. ❌ "Underwritten by our
insurance partners" (anonymous) = disclosure failure. All performance claims must be sourced
and current.

### 7. Key Facts First, Details Later
Before consent, show the 5 key facts in fixed order: What is this? / What does it cover? /
What is NOT covered? / How long am I covered? / How much does it cost (incl. taxes)? Each
expandable. Exclusions are mandatory here — hiding "what's not covered" is the single most
challenge-prone omission. Then: "Full details, terms & conditions and exclusions are
available next" with one-tap access. CTA: "I Understand, Continue" + "View Full Policy
Details". ❌ Wall-of-text T&C with a lone "I agree" checkbox.

### 8. Guided Journey, Not a Form
One question per screen, progress indicator (You → Coverage → Review → Confirm → Done),
Save & Exit that actually resumes, data-safety reassurance line. Collect only what the step
needs (DPDP data minimisation). ❌ Six-field static forms up front.

### 9. Purposeful Visual Design
Plain language, empathy-first microcopy, clear hierarchy, trust elements. ❌ Dense legal
jargon, low-contrast disclosures, generic tone. Reassurance framing ("We've got you covered")
is fine on value screens; it must never appear styled as, or adjacent to, the consent action
where it could color the consent.

## Screen-by-screen checklist (audit shorthand)

| Screen | Must have | Must NOT have |
|---|---|---|
| Approval + offer | Approval confirmation first; product card w/ insurer identity; equal CTAs; optionality line | Offer before approval verdict; single forced CTA |
| Plan chooser | ₹0 option equal-styled; no pre-selection; per-tier pricing | Pre-ticked tier; hidden decline |
| Suitability | 2 questions max; stated basis for recommendation; skip path | Suitability checkbox theatre |
| Key facts | 5 facts incl. exclusions; T&C one tap away; cost incl. taxes | Consent on same tap as first sight of T&C |
| Consent | Individual per product; affirmative action; optionality line | Bundled checkboxes; pre-ticks |
| Payment/confirm | Premium matches KFS; net disbursal shown | New fees; drip pricing |
| Post-purchase | Policy doc delivery; free-look period notice (30 days per IRDAI Protection of Policyholders' Interests Regulations, 2024); cancellation path | Silence on free-look |

## CX levers that are compliance-positive

Daily-cost reframing; approval-moment placement; choice architecture (3 tiers); suitability
personalization; claims-performance trust strips; guided steps with progress. Each converts
better than its dark-pattern counterpart precisely because it informs rather than tricks —
use these as the "how to improve CX" suggestions in audit findings.
