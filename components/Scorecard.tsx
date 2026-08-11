'use client';

import type {
  AuditResult,
  Finding,
  Severity,
} from '@/lib/tool-schema';

const SEV_EMOJI: Record<Severity, string> = {
  red: '🔴',
  yellow: '🟡',
  green: '🟢',
  white: '⚪',
};

function countBySeverity(screens: AuditResult['screens']) {
  const c = { red: 0, yellow: 0, green: 0, white: 0 };
  for (const s of screens)
    for (const f of s.findings) c[f.severity]++;
  return c;
}

function FindingRow({ f }: { f: Finding }) {
  return (
    <div className="finding">
      <div className={`sev-pill sev-${f.severity}`}>{SEV_EMOJI[f.severity]}</div>
      <div className="finding-body">
        <div className="f-top">
          <span className="level-tag">{f.level}</span>
        </div>
        <div className="f-text">{f.finding}</div>
        <div className="f-meta">
          {f.rule && (
            <div className="kv rule">{f.rule}</div>
          )}
          {f.fix && (
            <div className="kv fix">
              <b>Fix:</b> {f.fix}
            </div>
          )}
          {f.cx_upside && (
            <div className="kv cx">
              <b>CX upside:</b> {f.cx_upside}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Scorecard({
  result,
  model,
  onReset,
}: {
  result: AuditResult;
  model?: string;
  onReset: () => void;
}) {
  const v = result.verdict;
  const tally = countBySeverity(result.screens);
  const score = Math.max(0, Math.min(100, v.compliance_score));
  const ringColor =
    score >= 80 ? 'var(--green)' : score >= 55 ? 'var(--yellow)' : 'var(--red)';

  const today = new Date().toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  function printReport() {
    document
      .querySelectorAll('details.screen-block')
      .forEach((d) => d.setAttribute('open', ''));
    window.print();
  }

  function copyMarkdown() {
    navigator.clipboard.writeText(toMarkdown(result, today)).then(
      () => alert('Audit copied as Markdown — paste into Notion, Slack, or a doc.'),
      () => alert('Copy failed — your browser blocked clipboard access.')
    );
  }

  return (
    <div>
      <div className="toolbar">
        <button className="ghost-btn" onClick={copyMarkdown}>
          Copy as Markdown
        </button>
        <button className="ghost-btn" onClick={printReport}>
          Print / Save PDF
        </button>
        <button className="ghost-btn" onClick={onReset}>
          New audit
        </button>
      </div>

      {/* Verdict card */}
      <div className="card">
        <div className="sc-header">
          <div>
            <p className="journey">
              {result.mode === 'DESIGN' ? 'Compliant flow spec' : 'SEBI compliance audit — Module B'} · {today}
            </p>
            <h2>{result.journey}</h2>
            <span className={`ship-badge ship-${v.ship_recommendation}`}>
              {v.ship_recommendation === 'Blocked'
                ? '⛔ Ship blocked'
                : v.ship_recommendation === 'Conditional'
                  ? '⚠️ Conditional'
                  : '✅ Clear to ship'}
            </span>
          </div>
          <div className="score-ring">
            <div
              className="ring"
              style={
                {
                  '--pct': score,
                  '--ring-color': ringColor,
                } as React.CSSProperties
              }
            >
              <div className="inner">{score}</div>
            </div>
            <div className="ring-label">
              Compliance
              <br />
              score
            </div>
          </div>
        </div>

        <div className="tally">
          <div className="tally-item">
            <div className="n n-red">{v.violations}</div>
            <div className="l">🔴 Violations</div>
          </div>
          <div className="tally-item">
            <div className="n n-yellow">{v.risks}</div>
            <div className="l">🟡 Risks</div>
          </div>
          <div className="tally-item">
            <div className="n n-green">{v.compliant}</div>
            <div className="l">🟢 Compliant</div>
          </div>
          <div className="tally-item">
            <div className="n n-white">{v.unverifiable}</div>
            <div className="l">⚪ Unverifiable</div>
          </div>
          <div className="tally-item">
            <div className="n">{v.screens_reviewed}</div>
            <div className="l">Screens</div>
          </div>
        </div>

        {result.summary && <div className="summary-box">{result.summary}</div>}

        {v.top_fixes?.length > 0 && (
          <div className="top-fixes">
            <h4>Top fixes by risk</h4>
            <ol>
              {v.top_fixes.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {/* Screen-by-screen */}
      {result.screens.length > 0 && (
        <>
          <div className="section-title">
            Screen-by-screen findings{' '}
            <span className="count">
              · {tally.red}🔴 {tally.yellow}🟡 {tally.green}🟢 {tally.white}⚪
            </span>
          </div>
          {result.screens.map((s, i) => {
            const c = { red: 0, yellow: 0, green: 0, white: 0 };
            s.findings.forEach((f) => c[f.severity]++);
            return (
              <details className="screen-block" key={i} open={c.red > 0}>
                <summary>
                  <span className="chev">▶</span>
                  <span className="screen-name">{s.name}</span>
                  <span className="mini-dots">
                    {(['red', 'yellow', 'green', 'white'] as Severity[]).map(
                      (sev) =>
                        c[sev] > 0 && (
                          <span className="dot" key={sev}>
                            {SEV_EMOJI[sev]} {c[sev]}
                          </span>
                        )
                    )}
                  </span>
                </summary>
                <div className="findings">
                  {s.findings.map((f, j) => (
                    <FindingRow f={f} key={j} />
                  ))}
                </div>
              </details>
            );
          })}
        </>
      )}

      {/* Banned pattern checklist */}
      {result.banned_patterns?.length > 0 && (
        <>
          <div className="section-title">Banned-pattern checklist</div>
          <div className="card" style={{ overflowX: 'auto' }}>
            <table className="pattern-table">
              <thead>
                <tr>
                  <th style={{ width: 30 }}>#</th>
                  <th>Pattern</th>
                  <th style={{ width: 70 }}>Result</th>
                  <th className="p-note-col">Evidence</th>
                </tr>
              </thead>
              <tbody>
                {result.banned_patterns.map((p) => (
                  <tr key={p.id}>
                    <td>{p.id}</td>
                    <td className="p-name">{p.pattern}</td>
                    <td>
                      <span className={`result-tag result-${p.result}`}>
                        {p.result === 'pass'
                          ? '✓ Pass'
                          : p.result === 'fail'
                            ? '✗ Fail'
                            : 'N/A'}
                      </span>
                    </td>
                    <td className="p-note">{p.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Fix backlog */}
      {result.fix_backlog?.length > 0 && (
        <>
          <div className="section-title">Fix backlog</div>
          <ol className="backlog">
            {result.fix_backlog.map((item, i) => (
              <li
                className={`backlog-item ${item.severity}-left`}
                key={i}
              >
                <span className="num">{item.priority}</span>
                <div className="backlog-body">
                  <div className="b-top">
                    <span>{SEV_EMOJI[item.severity]}</span>
                    <span className="b-screen">{item.screen}</span>
                    <span className="owner-tag">{item.owner}</span>
                  </div>
                  <div className="b-change">{item.change}</div>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}

      {/* Unverifiable */}
      {result.unverifiable?.length > 0 && (
        <>
          <div className="section-title">Couldn&apos;t verify</div>
          <ul className="unverif-list">
            {result.unverifiable.map((u, i) => (
              <li key={i}>
                {u.what}
                <div className="settle">→ {u.how_to_settle}</div>
              </li>
            ))}
          </ul>
        </>
      )}

      {/* Design spec (DESIGN mode) */}
      {result.design_spec_markdown && (
        <>
          <div className="section-title">Compliant flow spec</div>
          <div className="card design-spec">
            <pre>{result.design_spec_markdown}</pre>
          </div>
        </>
      )}

      <p className="footer-note">
        This review informs design and compliance decisions and is not legal
        sign-off. Effective-date-sensitive rules are noted inline, and SEBI
        consolidates circulars into master circulars — confirm the current clause
        before relying on a citation externally. Route genuinely ambiguous
        questions to compliance/legal.
        {model ? ` · Audited with ${model}` : ''}
      </p>
    </div>
  );
}

/** Serialize the audit to Markdown matching references/output-formats.md. */
function toMarkdown(r: AuditResult, date: string): string {
  const v = r.verdict;
  const L: string[] = [];
  L.push(`# RegSpine — SEBI Compliance Audit — ${r.journey} — ${date}`);
  L.push('');
  L.push('## Verdict at a glance');
  L.push(
    `- Screens reviewed: ${v.screens_reviewed} | 🔴 ${v.violations} violations | 🟡 ${v.risks} risks | 🟢 ${v.compliant} compliant | ⚪ ${v.unverifiable} unverifiable`
  );
  L.push(`- Compliance score: ${v.compliance_score}/100`);
  L.push(`- Ship recommendation: ${v.ship_recommendation}`);
  if (v.top_fixes?.length) {
    L.push(`- Top fixes by risk:`);
    v.top_fixes.forEach((f) => L.push(`  - ${f}`));
  }
  if (r.summary) {
    L.push('');
    L.push(r.summary);
  }
  L.push('');
  L.push('## Screen-by-screen findings');
  for (const s of r.screens) {
    L.push('');
    L.push(`### ${s.name}`);
    L.push('| Level | Finding | Sev | Rule | Fix | CX upside |');
    L.push('|---|---|---|---|---|---|');
    for (const f of s.findings) {
      L.push(
        `| ${f.level} | ${esc(f.finding)} | ${SEV_EMOJI[f.severity]} | ${esc(f.rule)} | ${esc(f.fix)} | ${esc(f.cx_upside)} |`
      );
    }
  }
  L.push('');
  L.push('## Banned-pattern checklist');
  L.push('| # | Pattern | Result | Evidence |');
  L.push('|---|---|---|---|');
  for (const p of r.banned_patterns) {
    L.push(`| ${p.id} | ${esc(p.pattern)} | ${p.result} | ${esc(p.note)} |`);
  }
  L.push('');
  L.push('## Fix backlog (ordered)');
  for (const item of r.fix_backlog) {
    L.push(
      `${item.priority}. ${SEV_EMOJI[item.severity]} [${item.screen}] ${item.change} — _${item.owner}_`
    );
  }
  if (r.unverifiable?.length) {
    L.push('');
    L.push("## Couldn't verify");
    for (const u of r.unverifiable) L.push(`- ${u.what} → ${u.how_to_settle}`);
  }
  if (r.design_spec_markdown) {
    L.push('');
    L.push('---');
    L.push(r.design_spec_markdown);
  }
  L.push('');
  L.push(
    '_This review informs design decisions and is not legal sign-off._'
  );
  return L.join('\n');
}

function esc(s: string): string {
  return (s || '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
}
