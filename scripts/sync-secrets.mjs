// Reads config/keys.json and pushes each key into the regspine-proxy Cloudflare
// Worker as a secret. Keys live ONLY here + in the Worker; they are never bundled
// into the static site. Run: `npm run sync-secrets`.
//
// The ACCESS_PASSWORD is deliberately NOT handled here — set it once by hand with
// `npx wrangler secret put ACCESS_PASSWORD` in worker/, so it never sits in a file.
//
// Auth: set CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID in the environment, or
// run `npx wrangler login` in worker/ first.
import { readFileSync, existsSync } from 'fs';
import { spawnSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const WORKER_DIR = path.join(ROOT, 'worker');
const KEYS_FILE = path.join(ROOT, 'config', 'keys.json');

// provider (in models.json / keys.json)  →  Worker secret name
const PROVIDER_SECRET = {
  anthropic: 'ANTHROPIC_API_KEY',
  google: 'GEMINI_API_KEY',
  openai: 'OPENAI_API_KEY',
};

if (!existsSync(KEYS_FILE)) {
  console.error(
    'Missing config/keys.json. Copy config/keys.example.json to config/keys.json and add your real keys.'
  );
  process.exit(1);
}

const keys = JSON.parse(readFileSync(KEYS_FILE, 'utf8'));
let pushed = 0;

for (const [provider, value] of Object.entries(keys)) {
  if (provider.startsWith('$')) continue; // skip $comment
  const secretName = PROVIDER_SECRET[provider];
  if (!secretName) {
    console.warn(`Skipping unknown provider "${provider}" (no Worker secret mapped).`);
    continue;
  }
  if (!value || String(value).includes('REPLACE-ME')) {
    console.warn(`Skipping "${provider}" — placeholder/empty value.`);
    continue;
  }
  console.log(`Pushing ${provider} → Worker secret ${secretName}…`);
  const res = spawnSync('npx', ['--yes', 'wrangler@latest', 'secret', 'put', secretName], {
    cwd: WORKER_DIR,
    input: String(value),
    stdio: ['pipe', 'inherit', 'inherit'],
    env: process.env,
  });
  if (res.status !== 0) {
    console.error(`Failed to set ${secretName}.`);
    process.exit(res.status || 1);
  }
  pushed++;
}

console.log(
  pushed
    ? `Done — ${pushed} secret(s) synced to regspine-proxy.\n` +
        `Remember to flip \`available\` in config/models.json for the providers you just loaded.`
    : 'Nothing to sync.'
);
