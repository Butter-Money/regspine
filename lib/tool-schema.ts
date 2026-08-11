import type Anthropic from '@anthropic-ai/sdk';

/**
 * Forced tool call that shapes Claude's audit into a strict scorecard the UI
 * can render deterministically. Mirrors references/output-formats.md.
 */

export type Severity = 'red' | 'yellow' | 'green' | 'white';
export type FindingLevel = 'Flow' | 'Screen' | 'Component';
export type PatternResult = 'pass' | 'fail' | 'na';

export interface Finding {
  level: FindingLevel;
  severity: Severity;
  finding: string;
  rule: string;
  fix: string;
  cx_upside: string;
}

export interface ScreenReport {
  name: string;
  findings: Finding[];
}

export interface BannedPattern {
  id: number;
  pattern: string;
  result: PatternResult;
  note: string;
}

export interface FixBacklogItem {
  priority: number;
  severity: Exclude<Severity, 'green' | 'white'>;
  screen: string;
  change: string;
  owner: string;
}

export interface Unverifiable {
  what: string;
  how_to_settle: string;
}

export interface AuditResult {
  mode: 'AUDIT' | 'DESIGN';
  journey: string;
  verdict: {
    screens_reviewed: number;
    violations: number;
    risks: number;
    compliant: number;
    unverifiable: number;
    ship_recommendation: 'Blocked' | 'Conditional' | 'Clear';
    compliance_score: number;
    top_fixes: string[];
  };
  screens: ScreenReport[];
  banned_patterns: BannedPattern[];
  fix_backlog: FixBacklogItem[];
  unverifiable: Unverifiable[];
  summary: string;
  design_spec_markdown?: string;
}

export const AUDIT_TOOL: Anthropic.Tool = {
  name: 'submit_audit',
  description:
    'Return the completed design-compliance audit as a structured scorecard. Call this exactly once, after you have finished reasoning through the design at flow, screen, and component level.',
  input_schema: {
    type: 'object',
    properties: {
      mode: {
        type: 'string',
        enum: ['AUDIT', 'DESIGN'],
        description:
          'AUDIT if an existing design/flow was reviewed; DESIGN if a new compliant journey was requested and produced.',
      },
      journey: {
        type: 'string',
        description:
          'The journey(s) the design belongs to, e.g. "Loan offer + embedded insurance attach".',
      },
      verdict: {
        type: 'object',
        properties: {
          screens_reviewed: { type: 'integer' },
          violations: { type: 'integer', description: 'Count of 🔴 findings.' },
          risks: { type: 'integer', description: 'Count of 🟡 findings.' },
          compliant: { type: 'integer', description: 'Count of 🟢 findings.' },
          unverifiable: {
            type: 'integer',
            description: 'Count of ⚪ findings.',
          },
          ship_recommendation: {
            type: 'string',
            enum: ['Blocked', 'Conditional', 'Clear'],
            description:
              'Blocked if any 🔴 exists; Conditional if only 🟡/⚪; Clear if fully compliant.',
          },
          compliance_score: {
            type: 'integer',
            minimum: 0,
            maximum: 100,
            description:
              'Overall 0–100 score. Any unresolved 🔴 should keep this well below 70.',
          },
          top_fixes: {
            type: 'array',
            items: { type: 'string' },
            description: 'Top 3 fixes by risk, most important first.',
          },
        },
        required: [
          'screens_reviewed',
          'violations',
          'risks',
          'compliant',
          'unverifiable',
          'ship_recommendation',
          'compliance_score',
          'top_fixes',
        ],
      },
      screens: {
        type: 'array',
        description:
          'One entry per screen (or logical section for text-described flows).',
        items: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            findings: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  level: {
                    type: 'string',
                    enum: ['Flow', 'Screen', 'Component'],
                  },
                  severity: {
                    type: 'string',
                    enum: ['red', 'yellow', 'green', 'white'],
                    description:
                      'red=violation, yellow=risk, green=compliant, white=unverifiable.',
                  },
                  finding: { type: 'string' },
                  rule: {
                    type: 'string',
                    description:
                      'Instrument + requirement, e.g. "RBI KFS Circular 2024-25/18 — APR before execution". Empty for green/white where n/a.',
                  },
                  fix: {
                    type: 'string',
                    description:
                      'Exact fix including suggested copy. Required for red/yellow.',
                  },
                  cx_upside: {
                    type: 'string',
                    description:
                      'How the compliant version converts as well or better.',
                  },
                },
                required: ['level', 'severity', 'finding', 'rule', 'fix', 'cx_upside'],
              },
            },
          },
          required: ['name', 'findings'],
        },
      },
      banned_patterns: {
        type: 'array',
        description:
          'All 15 hard-violation patterns from dark-patterns.md (1–12 cross-sector, 13–15 the SEBI securities addendum), each with a pass/fail/na result for this artifact.',
        items: {
          type: 'object',
          properties: {
            id: { type: 'integer', minimum: 1, maximum: 15 },
            pattern: { type: 'string' },
            result: { type: 'string', enum: ['pass', 'fail', 'na'] },
            note: {
              type: 'string',
              description: 'One line on why — evidence from the design.',
            },
          },
          required: ['id', 'pattern', 'result', 'note'],
        },
      },
      fix_backlog: {
        type: 'array',
        description: 'Ordered fix list — all 🔴 first, then 🟡.',
        items: {
          type: 'object',
          properties: {
            priority: { type: 'integer' },
            severity: { type: 'string', enum: ['red', 'yellow'] },
            screen: { type: 'string' },
            change: { type: 'string' },
            owner: {
              type: 'string',
              description: 'Suggested owner: design, copy, or eng.',
            },
          },
          required: ['priority', 'severity', 'screen', 'change', 'owner'],
        },
      },
      unverifiable: {
        type: 'array',
        description: 'Things that could not be verified from the artifacts.',
        items: {
          type: 'object',
          properties: {
            what: { type: 'string' },
            how_to_settle: {
              type: 'string',
              description: 'Exactly which artifact/detail would settle it.',
            },
          },
          required: ['what', 'how_to_settle'],
        },
      },
      summary: {
        type: 'string',
        description:
          'A 2–4 sentence plain-language executive summary of the review.',
      },
      design_spec_markdown: {
        type: 'string',
        description:
          'ONLY for DESIGN mode: the full compliant flow spec as markdown (flow diagram, per-screen specs, consent map, pre-build gate) per output-formats.md. Omit for AUDIT mode.',
      },
    },
    required: [
      'mode',
      'journey',
      'verdict',
      'screens',
      'banned_patterns',
      'fix_backlog',
      'unverifiable',
      'summary',
    ],
  },
};
