# Output Formats

## AUDIT mode — full scorecard report

Use this exact structure (.md by default; .docx via the docx skill on request):

```
# Design Compliance Audit — [Journey name] — [date]

## Verdict at a glance
- Screens reviewed: N | 🔴 X violations | 🟡 Y risks | 🟢 Z compliant | ⚪ W unverifiable
- Ship recommendation: [Blocked by 🔴s / Conditional / Clear]
- Top 3 fixes by risk: ...

## Screen-by-screen findings
### Screen 1 — [name/description]
| # | Level | Finding | Severity | Rule | Fix (with copy) | CX upside |
|---|-------|---------|----------|------|-----------------|-----------|
(Level = Flow / Screen / Component. One row per finding. 🟢 rows included.)

## Banned-pattern checklist result
(The 12-pattern table from dark-patterns.md with pass/fail/n.a. per pattern.)

## Fix backlog (ordered)
1. [🔴 first, then 🟡] — screen, change, owner-suggestion (design/copy/eng)

## Couldn't verify
- [what, and exactly which artifact/detail would settle it]

*This review informs design decisions and is not legal sign-off. Effective-date-sensitive
rules noted inline.*
```

Quick in-chat review: same findings, grouped by severity, no file — but always end with the
banned-pattern pass/fail summary and offer the full report.

## DESIGN mode — compliant flow spec

```
# [Journey name] — Compliant Flow Spec — [date]

## Flow diagram
(mermaid flowchart: screens as nodes, decision points as diamonds; mark every consent
point ⚡ and every mandatory-disclosure point 📋)

## Screens
### S1 — [Screen name]
- **Purpose**: one line
- **Components**: list (cards, CTA pair, fields, disclosures)
- **Things to remember (compliance)**: bullet rules that bind THIS screen, each with source
- **Component callouts**: per CTA/checkbox/price element — exact requirement
  (e.g. "Decline CTA: same size class as accept, adjacent, neutral label")
- **Suggested copy**: headline, body, CTA labels, reassurance line
- **CX guidance**: why this converts (tie to the pattern it implements)

## Consent map
| Consent point | Screen | What it covers | Standard it must meet |

## Pre-build gate
(dark-patterns.md checklist as a to-verify list for the design team)
```

Keep specs implementation-ready: a designer should be able to build frames from the spec
without asking what goes where; a PM should be able to trace every constraint to a rule.
