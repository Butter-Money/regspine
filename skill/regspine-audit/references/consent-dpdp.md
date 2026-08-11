# Consent & Data Journey — DPDP + digital-lending data rules

Sources: Digital Personal Data Protection Act, 2023 + DPDP Rules (notified 2025, phased
compliance); RBI Digital Lending Directions 2025 (data conduct); KYC MD. This rulebook is
about how consent and data collection must LOOK and BEHAVE in the UI.

## The DPDP consent standard (§5–§6, applied to screens)

Consent must be **free, specific, informed, unconditional, unambiguous, with clear
affirmative action**. Each word is a UI test:

| Standard | UI test | Fails when |
|---|---|---|
| Free | Declining doesn't punish the user beyond losing the specific feature | Consent wall for non-essential data; service degraded out of spite |
| Specific | One consent per purpose, purpose named in the consent line | "I agree to the processing of my data" (unspecified) |
| Informed | Notice before/with the ask: what data, why, who it's shared with, rights, how to complain | Notice only inside a linked 40-page policy |
| Unconditional | Loan/service not conditioned on consent for unrelated processing (marketing, cross-sell) | "Agree to marketing to continue" |
| Unambiguous + affirmative | Untouched checkbox / explicit tap; silence ≠ consent | Pre-ticks, "by continuing you agree", inferred consent |

**Notice requirements**: itemised description of personal data, purpose, how to exercise
rights (correction, erasure, grievance), and Data Protection Board complaint route. Must be
available in English + the 22 Eighth-Schedule languages — design implication: language
selector on or before the notice screen.

**Withdrawal**: as easy as the grant. If consent was one tap, withdrawal must be ~one tap,
findable (settings → privacy/consents), and must state consequences plainly. Absent or
buried withdrawal = 🔴.

**Consent artefacts**: the design should show the user a record of what they consented to
(a "My consents" surface) — required for consent-manager interop and excellent for trust.

## Digital lending data rules (RBI overlay)

- **Need-based collection only**, with explicit prior consent per data type.
- **Never request** access to contacts, call logs, telephony, or media files. One-time
  camera/mic/location access allowed only for onboarding/KYC needs, with explicit consent.
- User options that must exist in the UI: deny specific data uses, revoke previously granted
  consent, restrict disclosure to third parties, and **request deletion** of data collected
  from them.
- Permission prompts must be contextual: ask for camera at the KYC selfie step with a
  one-line why — not a battery of OS permissions at app launch (launch-battery = 🟡, any
  banned permission = 🔴).

## Component-level consent checklist

- Every checkbox label: names data + purpose in one plain sentence. ("Allow Butter to fetch
  my credit report from CIBIL to show loan offers" ✅)
- No consent checkbox does double duty (T&C + data + marketing = 🔴 bundling).
- Marketing/WhatsApp comms consent: separate, optional, default-off.
- "Why we ask" microcopy near sensitive fields (income, PAN) — DPDP-informed and
  trust-building.
- Third-party sharing (bureau pulls, insurer data pass, account aggregator): named
  recipient category, at the moment of relevance.
- Account Aggregator flows: the AA consent screen standard (purpose, duration, frequency,
  data range) — don't paper over it with a single "fetch my statements" button that hides
  the AA consent behind auto-taps.

## Children & vulnerable users

If any journey can plausibly onboard a minor (co-applicant edge cases), age verification +
verifiable parental consent per DPDP §9. Usually N/A for Butter's borrowers; flag if a
design collects DOB but never branches on it.
