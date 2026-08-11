# Banned & Risky Patterns — the always-on checklist

Run this list on every audit, every journey. Primary sources: the CCPA Guidelines for
Prevention and Regulation of Dark Patterns 2023 (13 named patterns, applicable to all
platforms including securities-market intermediaries), SEBI's investor-protection instruments
(mandatory F&O risk disclosure, IA/RA advertisement code, investor charter, SCORES 2.0 and
SMART-ODR), DPDP Act 2023, RBI NBFC Responsible Business Conduct Amendment Directions, 2026
(effective 01-Jul-2026 — bans dark patterns in NBFC digital journeys, esp. insurance flows),
and RBI Digital Lending Directions 2025. Where a pattern is banned by a specific instrument,
cite it; where it's a CCPA-named dark pattern, cite that.

Patterns 1–12 are cross-sector. Patterns **13–15 are the SEBI securities addendum** at the
foot of this file — they run on every audit too, marked `na` where there's no securities
surface.

## 🔴 Hard violations (ship-blockers)

| # | Pattern | What it looks like in a design | Why banned |
|---|---------|-------------------------------|------------|
| 1 | **Pre-ticked opt-in** | Insurance/add-on/consent checkbox already checked; toggle defaulted on; a plan pre-selected with no ₹0 option | Consent must be an affirmative act — RBI 2026 Conduct Directions; DPDP §6 (clear affirmative action); CCPA "false urgency"-adjacent |
| 2 | **Bundled consent** | One checkbox covering T&C + insurance + data sharing + marketing | Individual consent per product with its own T&C gate — RBI 2026; DPDP requires purpose-specific consent |
| 3 | **Conditioning loan on insurance** | "Complete insurance step to proceed", insurance screen with no skip path, disbursal blocked until cover selected | Loan approval must never be conditioned on insurance purchase — RBI 2026; also IRDAI misselling |
| 4 | **Unequal choice prominence** | Bold filled "Add Protection" vs tiny grey "skip" text link; decline hidden below the fold; opt-out behind an extra tap | Equal placement/clear choices required — RBI 2026 ("fix button weights"). Nuance: a filled accept + same-size outlined decline, adjacent, is acceptable; a text-link decline is not |
| 5 | **Confirm-shaming** | "No, I don't care about my family's safety" as the decline label | CCPA dark pattern ("confirm shaming"); RBI 2026 conduct |
| 6 | **Hidden or absent opt-out** | No "continue without insurance" path; cancellation buried in settings; consent withdrawal harder than grant | DPDP: withdrawal as easy as giving consent; RBI 2026 |
| 7 | **Charges outside KFS** | Fee shown at payment step that wasn't in the Key Facts Statement; "convenience fee" appearing at checkout | RBI KFS Circular 2024-25/18 — charges not in KFS cannot be levied |
| 8 | **Drip pricing** | Premium/fee revealed only at the final step; taxes added after price was anchored | CCPA named pattern; KFS all-inclusive APR rule |
| 9 | **False urgency / scarcity** | "Offer expires in 09:59" countdowns on insurance or loan offers that don't actually expire | CCPA named pattern; conduct risk under FPC |
| 10 | **Forced action for data** | Demanding contacts/gallery/location access to proceed with a loan app | Digital Lending Directions: no access to contacts, call logs, media; need-based data only |
| 11 | **Biased multi-lender display** | Sorting lender offers by commission; "recommended" flag without disclosed basis on an aggregator screen | Digital Lending Directions 2025 — unbiased display, lender identity disclosed (from 01-Nov-2025) |
| 12 | **Interface interference on consent** | Consent/decline styled to be missable (low contrast, tiny type), trick wording with double negatives | CCPA "interface interference"; DPDP informed-consent standard |

## 🟡 Risk patterns (challenge-prone — fix or justify)

- **Default-selected "Recommended" tier** in a Basic/Plus/None chooser: a RECOMMENDED badge is
  fine; pre-selecting the radio is risky — best practice is badge without pre-selection, or if
  pre-selected, the ₹0 "No protection" option must be equally prominent and one tap away.
- **Per-day price framing without total**: "₹3.28/day" is a proven, legitimate reframe — but
  the one-time/total premium must appear on the same screen with equal findability, taxes
  included. Daily-only display = 🟡 trending 🔴.
- **Trust claims without substantiation**: "Trusted by 2M+ borrowers", "99.5% claims settled"
  need a real, current data source. Unsubstantiated = misleading advertisement risk.
- **Skippable KFS**: KFS shown but "Continue" active with zero scroll/dwell — regulator expects
  a genuine opportunity to review (KFS validity period exists precisely for this).
- **Nudging language on neutral steps**: "protect the repayment risk" on the approval screen is
  accepted practice; the same nudge inside the consent checkbox label is not.
- **English-only journeys** where the borrower base is vernacular: KFS must be in a language
  the borrower understands; FPC requires vernacular display. Flag if no language switcher.

## 🔴 Securities addendum (SEBI-specific hard violations)

These three extend the numbered checklist to **15**. They run on every audit like the rest;
mark them `na` when the artifact has no securities surface.

| # | Pattern | What it looks like in a design | Why banned |
|---|---------|-------------------------------|------------|
| 13 | **Missing mandatory risk disclosure** | A derivatives/F&O surface with no SEBI-mandated loss-statistic disclosure (or one shrunk into a footnote / behind a tap); an offer, advice or marketing surface with no market-risk disclaimer; a mutual-fund screen without the scheme-documents warning | SEBI mandatory risk disclosure for equity F&O (2024); SEBI advertisement code — the disclosure must sit where the risk-taking decision is made |
| 14 | **Assured-return or unsubstantiated performance claims** | "Guaranteed 18% p.a.", "risk-free returns", "our calls gave 40%" with no verifiable source, cherry-picked track records, celebrity/finfluencer return promises — or an advice/recommendation screen with no SEBI registration number and category on it | Prohibited for registered intermediaries; SEBI IA/RA advertisement code requires registration identity on-screen and substantiated, non-misleading claims |
| 15 | **No reachable grievance / SCORES / ODR route** | Grievance path absent, or buried so it is not discoverable from within the journey; no GRO/compliance-officer contact with TAT; no SCORES 2.0 escalation link; no Online Dispute Resolution (SMART-ODR) path | SEBI investor-charter and complaints-disclosure circulars; SCORES 2.0 and SMART-ODR circulars — the escalation route is part of the product, not an optional footer |

Securities manifestations of the general patterns above, to look for explicitly:

- **#1 pre-ticked opt-in** → research packs, advisory subscriptions, PMS or other add-on
  services pre-selected; the derivatives segment pre-enabled at account opening.
- **#2 bundled consent** → one "I agree" covering Rights & Obligations + Risk Disclosure
  Document + Do's & Don'ts + tariff sheet, or account operation + research cross-sell +
  marketing in a single checkbox.
- **#3 conditioning** → must activate F&O, or buy an advisory plan, to open or operate the
  account; nomination forced with no opt-out declaration.
- **#8 drip pricing** → brokerage, STT, exchange/statutory charges and GST revealed only after
  the order executes instead of on the confirmation screen.
- **#9 false urgency** → countdowns on IPO/NFO/trade windows that don't reflect a real cut-off;
  "guaranteed allotment" framing.

## What compliant looks like (quick reference)

- Two CTAs, adjacent, same size class: `Add Protection` (filled) / `Continue Without Insurance`
  (outlined). Both above the fold.
- Standard reassurance line on every insurance screen: **"Insurance is optional and does not
  impact your loan approval."**
- One product, one consent, one screen. Each consent names its purpose.
- Every price: total amount incl. taxes + optional relatable framing.
- Every insurance offer: insurer name + logo + IRDAI regn. no. on-screen.
- Every advice/recommendation surface: entity name + SEBI registration number + category
  (broker / IA / RA) on-screen.
- Every derivatives surface: the mandated F&O loss disclosure, in body-text size, above the
  fold, on the same screen as the activation or order decision.
- Every order confirmation: all-in cost (brokerage + STT + exchange/statutory charges + GST)
  before the user commits.
- A persistent grievance entry point: GRO contact + TAT, SCORES 2.0 link, and the ODR path.
- Decline path completes the journey with zero additional friction.
