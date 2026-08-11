// ONE-COMMAND ROLLBACK — tears down the Cloudflare key proxy. Run: `npm run rollback`.
//
// RegSpine has no bring-your-own-key fallback, so after this the site cannot run
// audits until `proxyUrl` points at a proxy again. That is the intent: it is the
// kill switch for a leaked access password or a runaway spend.
//
// SAFETY: this touches ONLY the Worker named below. It never lists, modifies, or
// deletes any other Worker in the account — in particular it will not touch
// `design-audit-proxy`, which serves the separate design-compliance-audit tool.
// It makes no changes to git remotes, GitHub Pages, or anything outside this
// repo + the one named Worker.
//
// What it does:
//   1. Deletes the `regspine-proxy` Worker (and its secrets) from Cloudflare.
//   2. Sets proxyUrl back to "" in app.config.json (site stops calling any model).
// It then tells you to commit + push. Nothing else is affected.
//
// Auth: CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID in the environment, or
// `npx wrangler login` in worker/ first.
import { readFileSync, writeFileSync } from 'fs';
import { spawnSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const WORKER_NAME = 'regspine-proxy'; // hard-locked; never other Workers
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const WORKER_DIR = path.join(ROOT, 'worker');
const APP_CONFIG = path.join(ROOT, 'app.config.json');

console.log(`Rollback: removing ONLY the "${WORKER_NAME}" Worker and reverting proxyUrl.\n`);

// 1) Delete the Worker (name explicitly pinned so nothing else can be hit).
const del = spawnSync(
  'npx',
  ['--yes', 'wrangler@latest', 'delete', '--name', WORKER_NAME],
  { cwd: WORKER_DIR, stdio: ['pipe', 'inherit', 'inherit'], input: 'y\n', env: process.env }
);
if (del.status !== 0) {
  console.warn(
    `\nWorker delete returned non-zero (it may already be gone). Continuing with config revert.`
  );
}

// 2) Revert proxyUrl → "" so the site stops pointing at a dead proxy.
const cfg = JSON.parse(readFileSync(APP_CONFIG, 'utf8'));
const had = cfg.proxyUrl;
cfg.proxyUrl = '';
writeFileSync(APP_CONFIG, JSON.stringify(cfg, null, 2) + '\n', 'utf8');
console.log(`\napp.config.json proxyUrl: "${had}" → "" (audits disabled until a proxy is set).`);

console.log(
  `\nRollback complete for "${WORKER_NAME}". No other Worker or system was touched.\n` +
    `Finish by committing the config change:\n` +
    `  git add app.config.json && git commit -m "Rollback shared-key proxy" && git push\n`
);
