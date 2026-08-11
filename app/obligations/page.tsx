'use client';

import Link from 'next/link';
import TopBar from '@/components/TopBar';

const OBLIGATION_SCHEMA = `{
  "obligation_id": "OB-07",
  "applies_to": ["stock_broker"],
  "trigger": "end of each quarter",
  "frequency": "quarterly",
  "action_required": "settle the running account of client funds and securities",
  "evidence_artifact": "running account settlement statement sent to client",
  "deadline_rule": "within the timeline specified by the exchange",
  "source": { "circular": "Master Circular for Stock Brokers", "clause": "4.2", "page": 41 },
  "rationale": "protects client funds; prevents misuse of idle balances",
  "severity_if_missed": "high"
}`;

const CHANGE_SCHEMA = `{
  "obligation_id": "OB-07",
  "change": "modified",
  "was": "quarterly settlement",
  "now": "settlement within 3 working days of quarter-end",
  "source_amendment_clause": "2.1",
  "drafted_workflow_update": "…",
  "confidence": 0.9
}`;

const STEPS = [
  {
    title: 'Ingest',
    body: 'Upload a SEBI master circular. It is parsed into clauses with page anchors, so every downstream statement keeps a route back to the source text.',
  },
  {
    title: 'Extract — the auto-rulebook',
    body: 'One model call per clause batch returns structured obligations in the fixed schema below. This is a machine-generated rulebook in the same shape as the hand-written ones Module B already runs on.',
  },
  {
    title: 'Obligation graph',
    body: 'Browse the extracted obligations as a graph. Click any node to jump to its source clause in the circular — the same citation discipline the auditor enforces.',
  },
  {
    title: 'Change detection',
    body: 'Drop in an amendment. Each affected obligation is classified added / modified / superseded, and the updated workflow is drafted, cited to the amending clause.',
  },
  {
    title: 'Evidence & gap board',
    body: 'Track which obligations have evidence on file and which are open, with the artifact each one needs.',
  },
];

export default function Obligations() {
  return (
    <>
      <TopBar active="A" />

      <div className="wrap">
        <div className="page-head">
          <span className="module-chip">
            RegSpine · Module <span className="b">A</span> — Obligation Engine
          </span>
          <h1 style={{ marginTop: 14 }}>
            From regulatory issuance to <span className="accent">operational action</span>
          </h1>
        </div>
        <p className="tagline">
          Module A reads SEBI&apos;s regulatory text and writes the rulebook itself:
          clause-cited obligations, a browsable obligation graph, and change
          detection that tells you what an amendment actually changes in your
          workflow.
        </p>

        <div className="phase-banner">
          <span>🚧</span>
          <span>
            <b>Phase 2 — in build.</b> Module B (the auditor) is live and running
            real audits today. This page describes what Module A does and the exact
            schemas it produces; the engine itself is being built now.{' '}
            <Link href="/">Go to Module B →</Link>
          </span>
        </div>

        <div className="card">
          <div className="field-label">The pipeline</div>
          <ol className="pipeline">
            {STEPS.map((s, i) => (
              <li key={s.title}>
                <span className="step-n">{i + 1}</span>
                <div className="step-body">
                  <h4>{s.title}</h4>
                  <p>{s.body}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="loop-note">
            <b>The closed loop.</b> The obligations Module A extracts are written
            back into <code>skill/regspine-audit/references/</code> in the same
            markdown shape as the hand-authored rulebooks — so Module B can audit a
            broker screen against the rules RegSpine just wrote itself. One
            continuous system: regulation in, cited and scored compliance out.
          </div>
        </div>

        <div className="card">
          <div className="field-label">Obligation extraction — output schema</div>
          <pre className="schema-block">{OBLIGATION_SCHEMA}</pre>
        </div>

        <div className="card">
          <div className="field-label">Change detection — classification output</div>
          <pre className="schema-block">{CHANGE_SCHEMA}</pre>
        </div>

        <p className="footer-note">
          RegSpine informs design and compliance decisions — not legal sign-off.
          Extracted obligations carry their source clause so every one can be
          checked against the circular.
        </p>
      </div>
    </>
  );
}
