// One command for the one config file. Run: `npm run sync`.
//
// config/models.json is the single place you edit a model: name, availability,
// artifact types, and its API key. It is GIT-IGNORED because it holds real keys.
// This script does the two things that file implies:
//
//   1. Pushes each distinct provider key into the regspine-proxy Worker as a
//      secret (server-side only — a key never reaches a browser or the repo).
//   2. Writes config/models.public.json — the same list with every `key` field
//      stripped. That generated file is what the app imports and what CI builds
//      from, so it IS committed. Commit it after every sync.
//
// If config/models.json doesn't exist yet, it is bootstrapped from the public
// file with blank keys, so a fresh clone has something to fill in.
//
// The ACCESS_PASSWORD is deliberately not handled here — set it once by hand with
// `npx wrangler secret put ACCESS_PASSWORD` in worker/, so it never sits in a file.
//
// Cloudflare auth: CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID in the
// environment, or run `npx wrangler login` in worker/ first.
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { spawnSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const WORKER_DIR = path.join(ROOT, 'worker');
const EDITABLE = path.join(ROOT, 'config', 'models.json');
const PUBLIC = path.join(ROOT, 'config', 'models.public.json');

// provider → the Worker secret that holds its key. Keep in sync with worker/src/worker.js.
const PROVIDER_SECRET = {
  anthropic: 'ANTHROPIC_API_KEY',
  google: 'GEMINI_API_KEY',
  openai: 'OPENAI_API_KEY',
};

const isPlaceholder = (v) => !v || !String(v).trim() || /REPLACE-ME/i.test(String(v));

// ---------------------------------------------------------------- bootstrap

if (!existsSync(EDITABLE)) {
  if (!existsSync(PUBLIC)) {
    console.error('Neither config/models.json nor config/models.public.json exists.');
    process.exit(1);
  }
  const seed = JSON.parse(readFileSync(PUBLIC, 'utf8'));
  seed.$comment =
    'THE one file you edit. Per model: label (display name), available (green/red status), artifacts (comma-separated types it accepts), key (that provider API key). GIT-IGNORED — real keys live here. Run `npm run sync` after editing: it pushes the keys to the proxy Worker and regenerates config/models.public.json, which is what the site imports. Commit the .public.json.';
  seed.models = seed.models.map((m) => ({ ...m, key: '' }));
  writeFileSync(EDITABLE, JSON.stringify(seed, null, 2) + '\n');
  console.log('Bootstrapped config/models.json from models.public.json — add your keys, then re-run.');
  process.exit(0);
}

const cfg = JSON.parse(readFileSync(EDITABLE, 'utf8'));

// ---------------------------------------------------------------- validate

const errors = [];
const seen = new Set();
for (const m of cfg.models || []) {
  const where = `model "${m.id || '(no id)'}"`;
  if (!m.id) errors.push(`${where}: missing "id" (the provider's model id).`);
  if (!m.label) errors.push(`${where}: missing "label" (the name shown in the dropdown).`);
  if (!PROVIDER_SECRET[m.provider])
    errors.push(
      `${where}: provider "${m.provider}" is not one of ${Object.keys(PROVIDER_SECRET).join(', ')}.`
    );
  if (!m.artifacts) errors.push(`${where}: missing "artifacts" (e.g. "png,jpeg,webp,gif,pdf").`);
  if (seen.has(m.id)) errors.push(`${where}: duplicate id.`);
  seen.add(m.id);
  if (m.available === true && isPlaceholder(m.key))
    errors.push(`${where}: marked available but has no key. Add the key, or set available:false.`);
}
if (!seen.has(cfg.defaultModel))
  errors.push(`defaultModel "${cfg.defaultModel}" is not one of the listed models.`);

if (errors.length) {
  console.error('config/models.json has problems:\n' + errors.map((e) => `  - ${e}`).join('\n'));
  process.exit(1);
}

// ---------------------------------------------------------------- push keys

// One secret per provider. If two models of the same provider carry different
// keys, that's ambiguous — the proxy holds one key per provider, so say so.
const byProvider = new Map();
for (const m of cfg.models) {
  if (isPlaceholder(m.key)) continue;
  const prev = byProvider.get(m.provider);
  if (prev && prev.key !== m.key) {
    console.error(
      `Provider "${m.provider}" has two different keys ("${prev.id}" vs "${m.id}"). ` +
        `The proxy holds one key per provider — make them the same.`
    );
    process.exit(1);
  }
  byProvider.set(m.provider, { id: m.id, key: m.key });
}

let pushed = 0;
for (const [provider, { key }] of byProvider) {
  const secretName = PROVIDER_SECRET[provider];
  console.log(`Pushing ${provider} → Worker secret ${secretName}…`);
  const res = spawnSync('npx', ['--yes', 'wrangler@latest', 'secret', 'put', secretName], {
    cwd: WORKER_DIR,
    input: String(key),
    stdio: ['pipe', 'inherit', 'inherit'],
    env: process.env,
  });
  if (res.status !== 0) {
    console.error(`Failed to set ${secretName}.`);
    process.exit(res.status || 1);
  }
  pushed++;
}

// ------------------------------------------------- write the key-free copy

const publicCfg = {
  $comment:
    'AUTO-GENERATED by scripts/sync.mjs — do not edit by hand. Source of truth: config/models.json (git-ignored, holds the keys). This copy has every key stripped and is the ONLY model list the site imports, which is what keeps keys out of the browser bundle. Committed so CI can build.',
  defaultModel: cfg.defaultModel,
  models: cfg.models.map(({ key, ...rest }) => rest),
};
writeFileSync(PUBLIC, JSON.stringify(publicCfg, null, 2) + '\n');

const live = publicCfg.models.filter((m) => m.available !== false).map((m) => m.id);
console.log(
  `\nWrote config/models.public.json — ${publicCfg.models.length} models, keys stripped.\n` +
    `${pushed} provider key(s) synced to regspine-proxy.\n` +
    `Available: ${live.length ? live.join(', ') : 'none'}\n\n` +
    `Commit config/models.public.json to push this to the live site.`
);
