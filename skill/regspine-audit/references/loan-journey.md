# Loan Journey — rulebook (onboarding → offer → KYC → sanction → disbursal)

Sources: RBI Digital Lending Directions 2025; KFS Circular RBI/2024-25/18; Fair Practices
Code (SBR MD 2023); Master Direction on KYC; Penal Charges Circular 2023-24/53. For clause
text or currency checks, consult the financial-regulatory-guidelines skill's knowledge base.

## Offer & pricing screens

- **KFS before execution** — every retail term loan gets a standardised Key Facts Statement
  before agreement execution: all-inclusive **APR**, repayment schedule, all charges, unique
  proposal number. Design implication: a dedicated KFS review screen, downloadable, with a
  validity window (min 3 working days for tenor ≥ 7 days) — the user must be able to leave
  and come back within validity without the offer changing.
- **No charges outside KFS** — audit every fee shown anywhere in the flow against the KFS
  screen. Any fee appearing later (processing top-up, "convenience fee", insurance premium
  added to disbursal) that isn't in the KFS = 🔴.
- **APR, not teaser rates** — headline rate displays must not contradict or bury the APR.
  "Starting at 8.5%*" with APR in a footnote = 🟡; APR absent = 🔴.
- **Penal charges** — shown as charges (not penal *interest*), disclosed upfront in KFS and
  in the loan agreement screens; no capitalisation.
- **Net disbursal transparency** — if any deduction happens (fees, premium), show the net
  credited amount before confirmation.

## Multi-lender / marketplace screens (Butter's aggregator surface)

From 01-Nov-2025 (Digital Lending Directions 2025):
- Display all matched lender offers **unbiasedly** — disclosed sort basis (rate, EMI), no
  commission-driven ordering.
- **Lender identity** (RE name) visible on every offer card — not just "Offer 1".
- No impermissible nudging toward a particular lender; "Recommended" flags need a stated,
  user-relevant basis.
- Butter (as LSP) branding must not obscure who the actual lender is.

## KYC screens

- Collect only KYC-required data at the KYC step (data minimisation).
- Video-KYC per KYC Master Direction where used: consent before starting, live-location
  capture disclosure, retake path.
- OTP-based e-KYC limits apply for account thresholds — flag flows that treat e-KYC as
  unlimited full KYC.
- Show why each document is needed; provide a failure/manual-review path that doesn't
  dead-end the applicant.

## Sanction, agreement & disbursal

- Sanction letter / terms shown in-app, downloadable, before acceptance.
- Explicit borrower acceptance action for the agreement (no "continue = accept").
- **Direct flow of funds**: disbursal RE → borrower account; no LSP pass-through wallet
  shown as receiving account. Repayments likewise direct.
- **Cooling-off / look-up period** (digital lending): borrower can exit the loan by paying
  principal + proportionate APR without penalty within the RE's stated cooling-off window —
  the journey must surface this right post-disbursal, not hide it.
- Post-disbursal screen: repayment schedule, grievance contact, and where to find the KFS
  again.

## Cross-journey requirements (Fair Practices Code)

- Language: KFS and key documents in a language the borrower understands; provide a language
  switcher on decision screens where the base is vernacular.
- Grievance Redressal Officer contact reachable from within the journey (footer/help).
- All communications non-misleading: no "guaranteed approval", no urgency theatre on rates.
- **Approval claims must be real**: an "Approved!" banner is only compliant after actual
  credit decisioning. "Approved" shown at application-submission (before underwriting) is a
  misleading representation — and if it anchors an insurance upsell, it compounds into a
  conditioning violation. Verify WHERE in the backend flow the screen sits, not just its copy.
- Rejection screens: communicate outcome honestly; don't loop rejected users back into the
  funnel with misleading "you're pre-approved elsewhere!" hooks unless the offer is real.

## Design-mode defaults for loan flows

Progress model: Details → Offers → KFS Review → KYC → Agreement → Disbursal, with Save &
Exit everywhere, a persistent help/grievance entry point, and per-step data-use notes
("Why we ask" microcopy — pairs DPDP compliance with trust-building CX).
