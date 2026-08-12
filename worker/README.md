# regspine-proxy — shared-key proxy (Cloudflare Worker)

A tiny proxy so RegSpine can run on shared provider keys without those keys ever
being exposed on the public site. The keys live here, server-side; the site sends
a shared **access password** that this Worker checks before forwarding upstream.

```
Browser (site)  ──POST, header: x-access-password──▶  this Worker
                                                        │ injects the real
                                                        │ provider API key
                                                        ▼
                            api.anthropic.com · generativelanguage… · api.openai.com
```

This is a **separate Worker from `design-audit-proxy`** (which serves the
design-compliance-audit tool). RegSpine gets its own password and its own spend,
so the demo password can be shared publicly and rotated without disturbing the
internal team tool.

## Deploy (once)

You need a Cloudflare account (free tier is fine) and Node installed.

```bash
cd worker
npx wrangler login                          # opens the browser to authorize
npx wrangler secret put ACCESS_PASSWORD     # invent the demo/team password
npx wrangler deploy
```

Then load the provider keys. From the repo root:

```bash
npm run sync        # pushes every key in config/models.json into this Worker
```

`wrangler deploy` prints the Worker URL, e.g.
`https://regspine-proxy.<your-subdomain>.workers.dev`.

Wire the site to it:

1. Open [`app.config.json`](../app.config.json) at the repo root.
2. Set `"proxyUrl"` to your Worker URL.
3. In `config/models.json`, set `available: true` for the models whose keys you just
   loaded (and `false` for the rest), then re-run `npm run sync`.
4. Commit `app.config.json` and `config/models.public.json` — Pages redeploys automatically.

The site asks every user for that **access password**. It never asks for an API key —
there is no bring-your-own-key path in RegSpine.

## Configuration

- **`ALLOWED_ORIGINS`** (in [`wrangler.toml`](./wrangler.toml)) — the site origin(s)
  allowed to call the Worker via CORS. Default is `https://butter-money.github.io`,
  which covers `https://butter-money.github.io/regspine/`. Change it if you move to
  a custom domain, then re-run `npx wrangler deploy`.
- **Secrets** — `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ALLOWED_MODELS`,
  `ACCESS_PASSWORD`. Provider keys and `ALLOWED_MODELS` are set by `npm run sync`; the password
  is set once by hand with `wrangler secret put` so it never sits in a file. Rotate any time by
  re-running.
- **`ALLOWED_MODELS`** — comma-separated model ids this proxy will run; anything else gets a
  403. Not secret, but stored as a secret so `npm run sync` can update it without a redeploy.
  It exists because provider keys are **account-wide**: a console key cannot be scoped to one
  model, so the proxy is the only place a model restriction can live.

## Notes & limits

- The password gate stops random visitors who find the Worker URL from spending your credits,
  and `ALLOWED_MODELS` caps what they could run even with it. Anyone with the password can
  still use the shared keys on the enabled models, so treat it as a shared password and rotate
  if it leaks. **Put a monthly spend limit on each key in the provider console as a backstop**
  — this matters more than usual here, because the password is published in the submission
  form and shown in the video.
- The Worker only forwards the three POST routes listed in
  [`src/worker.js`](./src/worker.js) and nothing else.
- Undo everything with `npm run rollback` from the repo root — it deletes **only**
  the `regspine-proxy` Worker and reverts `proxyUrl`.
