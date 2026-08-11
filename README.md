# RegSpine

**Agentic compliance — from SEBI's regulatory text to operational action.**
By **Butter Money** · SEBI Securities Market TechSprint @ GFF 2026 · Problem Statement 2.

RegSpine turns SEBI's regulatory text into automated, cited, actionable compliance. It ships as
one platform with two modules, in one repo, on one stack.

**Live:** <https://butter-money.github.io/regspine/>

---

## The two modules

### Module B — Interface & Communication Auditor · **live**

Audits investor-facing broker/adviser **screens, PDFs and communications** against SEBI's
investor-protection surface and returns a **scored report**: per finding, the **cited rule**,
the **exact fix (with copy)**, and a **CX upside**.

- **Input** — a screen (PNG/JPEG/WebP/GIF/PDF, ≤10 MB) or a pasted flow description.
- **Journeys** — *Securities / broker & adviser app* (primary), plus loan, embedded insurance,
  consent/DPDP and grievance, so the same auditor covers Butter Money's lending surfaces too.
- **Always-on** — the banned-pattern checklist: 12 cross-sector patterns plus 3 SEBI additions
  (missing mandatory risk disclosure, assured-return/unsubstantiated claims, no reachable
  SCORES/ODR route).
- **Output** — verdict at a glance (compliance score, ship recommendation, 🔴🟡🟢⚪ tally),
  screen-by-screen findings, banned-pattern checklist result, ordered fix backlog, and an
  honest "couldn't verify" list. Export as Markdown or print to PDF.

Every audit is a live model call against the artifact you upload. Nothing is cached, seeded or
pre-computed — there is no demo mode, by design.

### Module A — Obligation Engine · **phase 2, in build**

Ingests a SEBI master circular → extracts **clause-cited obligations** in a fixed JSON schema →
**obligation graph** with click-to-clause → **change detection** on an amendment
(added / modified / superseded, plus a drafted workflow update) → evidence & gap board.

Route: [`/obligations`](https://butter-money.github.io/regspine/obligations/) — it currently
documents the pipeline and the exact output schemas. **The closed loop:** the obligations
Module A extracts are written back into `skill/regspine-audit/references/` in the same markdown
shape as the hand-authored rulebooks, so Module B can audit a screen against the rules RegSpine
wrote itself.

> RegSpine informs design and compliance decisions — **it is not legal sign-off.** SEBI
> consolidates circulars into master circulars that supersede prior ones; confirm the current
> clause before relying on a citation externally.

---

## How it works

```
Browser (upload a screen + the access password)
   │  screenshots / PDF as base64, plus text + the selected journey
   │  system prompt = SKILL.md + every rulebook   (embedded by scripts/embed-skill.mjs)
   │  forced tool call `submit_audit` → strict scorecard schema   (lib/tool-schema.ts)
   ▼
regspine-proxy (Cloudflare Worker — holds the API keys, checks the password)
   ▼
Claude / Gemini / OpenAI  →  AuditResult  →  <Scorecard/>
```

There is **no server in the app** — it's a static export on GitHub Pages, which is what makes
it deployable to a public URL in a couple of minutes. The only server-side component is the
proxy, and its whole job is to hold the API keys so they never reach a browser.

### The rulebooks are the audit logic

`skill/regspine-audit/` is the single source of truth. `SKILL.md` carries the methodology; the
`references/*.md` files are the encoded regulation. [`scripts/embed-skill.mjs`](scripts/embed-skill.mjs)
reads them on every `dev`/`build` and generates `lib/skill-content.ts`, which becomes the model's
system context. **Edit the markdown and the audit changes — no code change.**

```
skill/regspine-audit/
├─ SKILL.md                       # Module B methodology: ingest → classify → audit → deliver
└─ references/
   ├─ dark-patterns.md            # always-on checklist (1–12 cross-sector, 13–15 SEBI)
   ├─ securities-journey.md       # SEBI investor protection — the primary rulebook
   ├─ loan-journey.md             # RBI digital lending & KFS
   ├─ insurance-journey.md        # IRDAI disclosure & embedded-attach patterns
   ├─ consent-dpdp.md             # DPDP consent UX
   ├─ grievance-journey.md        # GRO, TAT, escalation
   └─ output-formats.md           # the report shapes
```

Adding a journey = drop a new `references/*.md` in, list it in `scripts/embed-skill.mjs` and
add one entry to the `JOURNEYS` array in [`app/page.tsx`](app/page.tsx).

---

## Run locally

```bash
npm install
npm run dev            # http://localhost:3000
```

With no proxy configured the app is in **bring-your-own-key** mode: click **Add key**, paste an
Anthropic key, run an audit. The key is stored only in your browser and sent only to Anthropic.

## Configuration — the three files you edit

| File | Committed? | Holds |
|---|---|---|
| [`config/models.json`](config/models.json) | ✅ yes (no secrets) | The **model list** in the dropdown — `id`, `label`, `provider`, `available` — plus `defaultModel`. Set `available: false` to grey a model out with a red "Unavailable today" status. |
| `config/keys.json` | ❌ **git-ignored** | The **API keys**, keyed by provider. Copy [`config/keys.example.json`](config/keys.example.json) and fill it in. Pushed to the proxy Worker by `npm run sync-secrets`; **never** bundled into the site. |
| [`app.config.json`](app.config.json) | ✅ yes | `maxTotalMB` and `proxyUrl` (empty = bring-your-own-key; set = shared key via the proxy). |

> ⚠️ **Never put an API key in the repo or in `app.config.json`.** This is a static site, so
> anything in the repo ships to every visitor's browser. A shared key must live in the proxy.

`provider` values map to the proxy's upstreams: `anthropic` → the Claude Messages API (**the
only provider that accepts PDF input**), `google` → Gemini direct, `openai` → OpenAI direct.

## Deploy

### 1. The proxy (once)

```bash
cd worker
npx wrangler login
npx wrangler secret put ACCESS_PASSWORD
npx wrangler deploy
```

Then load the provider keys and point the site at the Worker:

```bash
cp config/keys.example.json config/keys.json   # add the real keys
npm run sync-secrets                           # pushes them into regspine-proxy
```

Set `proxyUrl` in `app.config.json` to the Worker URL, flip `available` in
`config/models.json` for the providers you loaded, and commit. Full detail and the rollback
path: [`worker/README.md`](worker/README.md).

### 2. The site

[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) builds the static export and
publishes it on every push to `main`. One-time setup: **Settings → Pages → Build and
deployment → Source = GitHub Actions**. The base path is resolved automatically by
`actions/configure-pages`, so nothing is hard-coded.

---

## Finding schema (Module B)

| Field | Meaning |
|---|---|
| `level` | Flow / Screen / Component |
| `severity` | 🔴 violation · 🟡 risk · 🟢 compliant · ⚪ unverifiable |
| `rule` | instrument + requirement, cited |
| `fix` | the exact change, with suggested copy |
| `cx_upside` | how the compliant version converts as well or better |

Full structure in [`lib/tool-schema.ts`](lib/tool-schema.ts); the report shapes it renders into
are in [`skill/regspine-audit/references/output-formats.md`](skill/regspine-audit/references/output-formats.md).

## Project layout

```
app/
  page.tsx                Module B — upload / paste UI, credential panel, model picker
  obligations/page.tsx    Module A — the phase-2 route
  globals.css             dashboard + print styles (navy + gold)
components/
  Scorecard.tsx           renders the AuditResult + Markdown export
  TopBar.tsx              wordmark + module switcher
lib/
  config.ts               reads app.config.json + config/models.json
  audit-client.ts         calls the model from the browser — direct (BYOK) or via the proxy
  prompt.ts               builds the system prompt from the skill
  tool-schema.ts          submit_audit tool → the scorecard shape
  skill-content.ts        generated from skill/ on dev/build (git-ignored)
scripts/
  embed-skill.mjs         embeds the rulebooks into the build
  sync-secrets.mjs        pushes config/keys.json into the proxy Worker
  rollback-all.mjs        deletes ONLY regspine-proxy and reverts to BYOK
skill/regspine-audit/     the audit logic — SKILL.md + references/*.md (source of truth)
worker/                   regspine-proxy (Cloudflare Worker) + deploy guide
.github/workflows/deploy.yml
```

## Limits & notes

- **Attachments:** PNG · JPEG · WebP · GIF · PDF, up to **10 MB** total per audit. PDFs are
  Claude-only; the app tells you before spending a call.
- **Screenshots beat text.** Component-level findings (pre-ticked boxes, CTA weights, whether a
  risk disclosure is above the fold) need pixels. Text-only reviews explicitly flag what can't
  be visually confirmed.
- **Citations.** The rulebooks are the design-applied layer, not the statute. Where the model is
  confident of a requirement but not the exact clause, it says so rather than inventing one.
- Regulations move. Keep `skill/regspine-audit/references/` current — that's what Module A
  automates.

## Team

Butter Money — Suhail Manocha (Founder & CEO) · Rohit (CTO).
