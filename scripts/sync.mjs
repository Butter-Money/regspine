// One command for the one config file. Run: `npm run sync`.
//
// config/models.json is the single place you configure RegSpine's models. It has
// two sections, because that's the shape reality has:
//
//   providers — ONE API key per provider. A console key authorises an ACCOUNT,
//               not a model; there is no such thing as a per-model key.
//   models    — what appears in the dropdown: name, availability, artifact types,
//               and which provider it bills to.
//
// The file is GIT-IGNORED because it holds real keys. This script does the three
// things it implies:
//
//   1. Pushes each provider key into the regspine-proxy Worker as a secret
//      (server-side only — a key never reaches a browser or the repo).
//   2. Pushes ALLOWED_MODELS: the ids of the models marked available. The Worker
//      refuses any other model id, so a leaked access password can't be pointed
//      at a model you didn't intend to pay for. This is the only model-level
//      restriction that exists — a key cannot give you one.
//   3. Writes config/models.public.json — the model list with the whole providers
//      section dropped. That generated file is what the app imports and what CI
//      builds from, so it IS committed. Commit it after every sync.
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

function putSecret(name, value) {
  const res = spawnSync('npx', ['--yes', 'wrangler@latest', 'secret', 'put', name], {
    cwd: WORKER_DIR,
    input: String(value),
    stdio: ['pipe', 'inherit', 'inherit'],
    env: process.env,
  });
  if (res.status !== 0) {
    console.error(`Failed to set ${name}.`);
    process.exit(res.status || 1);
  }
}

// ---------------------------------------------------------------- bootstrap

if (!existsSync(EDITABLE)) {
  if (!existsSync(PUBLIC)) {
    console.error('Neither config/models.json nor config/models.public.json exists.');
    process.exit(1);
  }
  const seed = JSON.parse(readFileSync(PUBLIC, 'utf8'));
  seed.$comment =
    'THE one file you edit. `providers` holds one API key per provider (a console key authorises an ACCOUNT, not a model). `models` lists what appears in the dropdown. GIT-IGNORED — real keys live here. Run `npm run sync` after editing.';
  seed.providers = Object.fromEntries(
    [...new Set(seed.models.map((m) => m.provider))].map((p) => [p, { key: '' }])
  );
  writeFileSync(EDITABLE, JSON.stringify(seed, null, 2) + '\n');
  console.log('Bootstrapped config/models.json — add your provider keys, then re-run.');
  process.exit(0);
}

const cfg = JSON.parse(readFileSync(EDITABLE, 'utf8'));
const providers = cfg.providers || {};

// ---------------------------------------------------------------- validate

const errors = [];
const seen = new Set();

for (const name of Object.keys(providers)) {
  if (name.startsWith('$')) continue;
  if (!PROVIDER_SECRET[name])
    errors.push(
      `providers."${name}" is not one of ${Object.keys(PROVIDER_SECRET).join(', ')}.`
    );
}

for (const m of cfg.models || []) {
  const where = `model "${m.id || '(no id)'}"`;
  if (!m.id) errors.push(`${where}: missing "id" (the provider's model id).`);
  if (!m.label) errors.push(`${where}: missing "label" (the name shown in the dropdown).`);
  if (!PROVIDER_SECRET[m.provider])
    errors.push(
      `${where}: provider "${m.provider}" is not one of ${Object.keys(PROVIDER_SECRET).join(', ')}.`
    );
  else if (!providers[m.provider])
    errors.push(`${where}: provider "${m.provider}" has no entry in the providers section.`);
  if (!m.artifacts) errors.push(`${where}: missing "artifacts" (e.g. "png,jpeg,webp,gif,pdf").`);
  if (seen.has(m.id)) errors.push(`${where}: duplicate id.`);
  seen.add(m.id);
  if (m.available === true && isPlaceholder(providers[m.provider]?.key))
    errors.push(
      `${where}: marked available, but providers."${m.provider}".key is empty. Add the key, or set available:false.`
    );
}
if (!seen.has(cfg.defaultModel))
  errors.push(`defaultModel "${cfg.defaultModel}" is not one of the listed models.`);

if (errors.length) {
  console.error('config/models.json has problems:\n' + errors.map((e) => `  - ${e}`).join('\n'));
  process.exit(1);
}

// ---------------------------------------------------------------- push keys

let pushed = 0;
for (const [name, entry] of Object.entries(providers)) {
  if (name.startsWith('$') || isPlaceholder(entry.key)) continue;
  console.log(`Pushing ${name} → Worker secret ${PROVIDER_SECRET[name]}…`);
  putSecret(PROVIDER_SECRET[name], entry.key);
  pushed++;
}

// ------------------------------------------- restrict what the keys can run

// The keys are account-wide, so the only place a model restriction can live is
// the proxy. Anything not in this list is refused with a 403.
const allowed = cfg.models.filter((m) => m.available !== false).map((m) => m.id);
console.log(`Pushing ALLOWED_MODELS (${allowed.length}) → Worker…`);
putSecret('ALLOWED_MODELS', allowed.join(','));

// ------------------------------------------- write the key-free copy

const publicCfg = {
  $comment:
    'AUTO-GENERATED by scripts/sync.mjs — do not edit by hand. Source of truth: config/models.json (git-ignored, holds the provider keys). This copy drops the providers section entirely and is the ONLY model list the site imports, which is what keeps keys out of the browser bundle. Committed so CI can build.',
  defaultModel: cfg.defaultModel,
  models: cfg.models,
};
writeFileSync(PUBLIC, JSON.stringify(publicCfg, null, 2) + '\n');

console.log(
  `\nWrote config/models.public.json — ${publicCfg.models.length} models, no keys.\n` +
    `${pushed} provider key(s) synced to regspine-proxy.\n` +
    `Runnable (and the only ids the proxy will accept): ${allowed.join(', ') || 'none'}\n\n` +
    `Commit config/models.public.json to push this to the live site.`
);
