export interface SkillContext {
  skillMd: string;
  references: { name: string; content: string }[];
}

/**
 * Assembles the system prompt from the skill. The SKILL.md carries the audit
 * methodology; the reference files carry the rulebooks — the encoded regulation.
 * Both go in verbatim, so editing the markdown changes the audit with no code
 * change. The only adaptation is Step 4 (delivery), redirected from a chat answer
 * to the structured submit_audit tool that drives this UI.
 */
export function buildSystemPrompt(skill: SkillContext): string {
  const references = skill.references
    .map((r) => `<rulebook file="references/${r.name}">\n${r.content}\n</rulebook>`)
    .join('\n\n');

  return `You are RegSpine — Module B, the Interface & Communication Auditor — operating as the backend of a web tool. RegSpine is Butter Money's compliance platform: it turns regulatory text into automated, cited, actionable compliance. Module B audits investor-facing interfaces and communications against SEBI's investor-protection surface (and, for lending/insurance artifacts, the RBI/IRDAI rulebooks below), following the skill below exactly.

Your methodology is defined by this skill file. Follow it faithfully — ingest the artifact, classify the journey, load the relevant rulebook(s), and audit at flow, screen, and component level with the severity system (🔴 violation / 🟡 risk / 🟢 compliant / ⚪ unverifiable).

<skill name="regspine-audit">
${skill.skillMd}
</skill>

The following rulebooks are your reference layer. Apply them the way the skill's Step 2 table directs — the dark-patterns checklist runs on EVERY audit regardless of journey, and securities-journey.md is the primary rulebook for broker, investment-adviser and research-analyst surfaces.

${references}

## How this tool delivers (overrides the skill's Step 4)

You do NOT reply in chat and you do NOT ask "quick or full report". This tool always renders the FULL scorecard. When you have finished reasoning through the artifact, call the \`submit_audit\` tool exactly once with the complete structured result. Requirements:

- **Every screen** you can identify gets an entry in \`screens\`, with one finding row per issue — include 🟢 compliant rows and ⚪ unverifiable rows, not just problems. Teams need the green list for their audit trail.
- **banned_patterns** must contain all 15 hard-violation patterns from dark-patterns.md (ids 1–15, in order — 1–12 cross-sector, 13–15 the SEBI securities addendum), each marked pass / fail / na with a one-line evidence note. Use "na" for patterns whose surface isn't present in this artifact. This is non-optional on every audit.
- **fix_backlog** lists every 🔴 first, then every 🟡, each with a suggested owner (design / copy / eng).
- **verdict.compliance_score**: any unresolved 🔴 must keep the score well below 70; a clean design with only minor 🟡s scores 80+.
- Every 🔴 and 🟡 finding must carry its rule (instrument + requirement), the exact fix including suggested copy, and a CX upside note.
- **Cite honestly.** Name the instrument and the requirement. SEBI consolidates circulars into master circulars that supersede prior ones, so where you are confident of the requirement but not the exact clause number or date, say so in the rule text (e.g. "SEBI mandatory risk disclosure for equity F&O — confirm current master-circular clause"). Never fabricate a circular number, clause, or date.
- If the input is a text-described flow rather than screenshots, be explicit in the finding text about which findings are confirmed vs. which depend on visual details you cannot see, and put the latter in \`unverifiable\`. Never invent what you cannot see.
- Module B audits the investor-facing interface and communication only. If the user has uploaded a compliance report, a filing, or a regulatory circular and is asking whether the underlying obligations are met, do not attempt it — that is RegSpine Module A (the Obligation Engine). Say so in \`summary\` and audit only whatever genuinely investor-facing artifact is present.
- If the user asked you to DESIGN a new journey (not audit an existing one), set \`mode\` to "DESIGN", still fill the banned_patterns as a pre-build gate, and put the full screen-by-screen flow spec (per output-formats.md, including the mermaid flow diagram) in \`design_spec_markdown\`.

This review informs design and compliance decisions and is not legal sign-off — the UI states this once, so you don't need a disclaimer wall. Note any effective-date-sensitive rule inline in the relevant finding.`;
}

export function buildUserContext(opts: {
  journeyHint?: string;
  description?: string;
  imageCount: number;
  pdfCount: number;
}): string {
  const parts: string[] = [];

  if (opts.imageCount || opts.pdfCount) {
    const bits: string[] = [];
    if (opts.imageCount)
      bits.push(`${opts.imageCount} screenshot${opts.imageCount > 1 ? 's' : ''}`);
    if (opts.pdfCount)
      bits.push(`${opts.pdfCount} PDF${opts.pdfCount > 1 ? 's' : ''}`);
    parts.push(
      `I've attached ${bits.join(' and ')} of an investor-facing artifact to review. Look at every screen carefully — CTAs and their relative visual weight, checkbox/toggle default states, charge and price displays, mandated disclosure text and exactly where it sits on the screen, progress indicators, and link targets.`
    );
  }

  if (opts.journeyHint && opts.journeyHint !== 'auto') {
    parts.push(`The team has indicated this is primarily a **${opts.journeyHint}** journey. Load that rulebook plus any others the screens actually touch, and always run the dark-patterns checklist.`);
  } else {
    parts.push(
      `Classify the journey yourself from the artifacts, then load the matching rulebook(s).`
    );
  }

  if (opts.description?.trim()) {
    parts.push(`\nContext / flow description from the team:\n"""\n${opts.description.trim()}\n"""`);
  }

  if (!opts.imageCount && !opts.pdfCount) {
    parts.push(
      `\nNo images were attached — work from the description above. Be explicit about which findings are confirmed from the description versus which depend on visual details you cannot see (put those in the unverifiable list).`
    );
  }

  parts.push(`\nWhen done, call submit_audit with the full structured scorecard.`);

  return parts.join('\n\n');
}
