# Securities Journey — rulebook (broker & investment-adviser apps: onboarding → trade/advice → grievance)

Sources: SEBI (Stock Brokers) Regulations & master circular for stock brokers; SEBI Investment
Advisers Regulations 2013 & Research Analysts Regulations 2014 (incl. advertisement code); SEBI
mandatory risk disclosure for equity F&O (2024); SEBI Investor Charter & complaints-disclosure
circulars; SCORES 2.0 and the Online Dispute Resolution (SMART-ODR) circulars; DPDP Act 2023; the
CCPA Guidelines for Prevention and Regulation of Dark Patterns 2023. **Confirm exact circular
numbers and current effective dates via the `financial-regulatory-guidelines` skill before citing
in a client-facing report** — SEBI circulars are consolidated into master circulars that supersede
prior ones.

Scope: apps/websites of stock brokers, investment advisers (IA), research analysts (RA), and
platforms distributing securities-market products (MFs, bonds, IPOs). Run `dark-patterns.md` on
every audit as well.

## Account opening / onboarding screens

- **Mandatory documents at account opening** — Rights & Obligations, Risk Disclosure Document
  (RDD), Do's & Don'ts, and the tariff/brokerage sheet must be presented on-screen before account
  activation, downloadable, not one tap away behind a generic "T&C" link. Bundled behind a single
  "I agree" = 🔴 (each mandated document needs a genuine review opportunity).
- **Nomination — offer, never force** — the flow must present *both* "add nominee" and an explicit
  "opt out of nomination" declaration with equal prominence. A flow that blocks progress unless a
  nominee is added, or hides the opt-out, is 🔴.
- **Segment activation (F&O / derivatives) is opt-in** — the derivatives segment must require
  explicit activation with the income-proof/eligibility step; never pre-enabled or bundled into
  the default account-opening path. Pre-selected "activate F&O" = 🔴.
- **KYC & data minimisation** — collect only KRA/KYC-required data at the KYC step; Aadhaar/e-KYC
  needs purpose-specific consent before capture (DPDP). Requesting device permissions (contacts,
  location, gallery) that the step doesn't need = 🔴 (forced action for data).

## Risk-disclosure screens (the securities-specific 🔴 to look for)

- **Mandatory F&O risk disclosure** — on any screen promoting or enabling equity derivatives
  trading, the SEBI-mandated disclosure that a large majority (~9 of 10) of individual F&O traders
  incur net losses must be displayed prominently (not a footnote, not behind a tap). Absent on an
  F&O/derivatives surface = 🔴; present but visually buried = 🟡. *(Verify current wording/threshold
  via financial-regulatory-guidelines.)*
- **Standard market-risk disclaimer** — "Investments in securities market are subject to market
  risks. Read all the related documents carefully before investing." on offer/advice/marketing
  surfaces. Missing = 🟡.
- **Mutual-fund distribution** — the standard warning "Mutual Fund investments are subject to
  market risks, read all scheme related documents carefully" wherever MF products are shown.
- **No assured / guaranteed returns, anywhere** — any "guaranteed 18% p.a.", "risk-free returns",
  "assured profit" copy is a 🔴 (misleading; prohibited for registered intermediaries).

## Advertising & claims (IA / RA / broker surfaces)

- **SEBI registration identity on-screen** — the entity's SEBI registration number and category
  (broker / IA / RA) must be visible on advice, recommendation, and marketing screens. Absent = 🔴.
- **Performance & testimonial claims** — past-performance must carry the standard disclaimer and a
  real, current data source; no cherry-picked/unsubstantiated track records. Unsubstantiated
  "our calls gave 40% returns" = 🔴. Testimonials/endorsements are restricted — flag celebrity or
  influencer endorsements making return claims (finfluencer restrictions apply to associations
  with unregistered persons).
- **Execution-only vs advice** — a broker execution screen must not present itself as personalised
  investment advice unless the entity is a registered IA and has done suitability. Blurring the two
  = 🟡 trending 🔴.

## Advisory / suitability screens (IA features only)

- **Risk profiling before advice** — personalised recommendations require a completed risk-profile
  and a suitability check first; advice screens that appear before any profiling = 🔴 (mirrors the
  insurance suitability rule).
- **Fee transparency** — IA fees must be displayed transparently and within the regulatory fee
  model/cap; hidden or post-hoc fees, or fees exceeding the permitted model, = 🔴. *(Confirm the
  current IA fee cap/model via financial-regulatory-guidelines.)*
- **Advisory subscription auto-renewal** — no silent auto-renew; renewal and cancellation must be
  as easy as sign-up, with clear consent (DPDP + dark-pattern "forced continuity").

## Order / transaction screens

- **Total-cost transparency before confirmation** — show brokerage + STT + exchange/statutory
  charges + GST, i.e. the all-in cost, before the order is placed; revealing charges only after
  execution = 🟡 trending 🔴 (drip pricing). This is the securities analogue of the KFS all-in rule.
- **Contract note & statement access** — a clear in-app path to contract notes, holdings and
  ledger; not buried.

## Consent / data (DPDP)

- Purpose-specific, unbundled consent — separate consent for account operation vs research/advisory
  cross-sell vs marketing; one blanket checkbox = 🔴.
- No pre-ticked consent or add-on services; withdrawal as easy as grant.
- Data minimisation at every step; "why we ask" microcopy pairs DPDP compliance with trust CX.

## Grievance / redressal (must be reachable from within the journey)

- **GRO / compliance-officer details** displayed with contact and TAT.
- **SCORES 2.0** link for escalation to SEBI, and the **Online Dispute Resolution (SMART-ODR)**
  path — both must be discoverable from help/footer, not absent. Missing SCORES/ODR route = 🔴.
- **Investor Charter** and periodic **complaints-data disclosure** available in-app.
- Complaint tracking with status/TAT; honest outcome communication.

## Cross-journey requirements

- Language: key disclosures in a language the investor understands where the base is vernacular;
  provide a switcher on decision screens.
- All communications non-misleading — no "guaranteed allotment" on IPOs, no urgency theatre on
  NFO/IPO windows that don't actually close as shown.
- Approval/allotment claims must be real — never show "allotted"/"approved" before the actual
  corporate/exchange event.

## Securities-specific dark patterns (add to the always-on checklist)

- Pre-ticked add-on services (research packs, PMS, advisory subscriptions) = 🔴.
- Forced bundling — must enable F&O / buy an advisory plan to open or use the account = 🔴.
- Confirm-shaming on opting out of a product ("No, I don't want to grow my wealth") = 🔴.
- Nudging users into higher-risk segments (F&O, leverage, MTF) without the mandated risk
  disclosure on the same screen = 🔴.
- False urgency on IPO/NFO/trade windows; countdowns that don't reflect a real cut-off = 🔴.

## Design-mode defaults for securities flows

Progress model: Account details → KYC (KRA) → Nomination (add *or* opt-out) → Segment selection
(cash default; F&O opt-in with risk disclosure) → Funding → Trade/Advice → Post-trade (contract
note, holdings, grievance/SCORES entry point). Save & Exit everywhere; a persistent
help/grievance entry point; the mandated risk disclosures rendered on the screens where the
risk-taking decision actually happens; "why we ask" microcopy on every data-collection step.

*This rulebook is the design-applied layer; for exact clause text, current circular numbers, and
effective-date checks, consult the `financial-regulatory-guidelines` skill.*
