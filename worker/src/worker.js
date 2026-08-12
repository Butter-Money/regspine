/**
 * regspine-proxy — shared-key proxy for the RegSpine site.
 *
 * Why this exists: RegSpine is a static app with no backend, so it can't hold a
 * shared secret. This Worker does. It keeps the provider API keys server-side
 * (never shipped to browsers) and only forwards requests that present the shared
 * ACCESS_PASSWORD. Users enter that password in the site instead of a key.
 *
 * Secrets/vars (set with `wrangler secret put` / in wrangler.toml):
 *   ANTHROPIC_API_KEY   (secret) — Claude key. Required for PDF input.
 *   GEMINI_API_KEY      (secret) — Google AI Studio key for Gemini direct, optional.
 *   OPENAI_API_KEY      (secret) — OpenAI key, optional.
 *   ACCESS_PASSWORD     (secret) — shared password the site must send.
 *   ALLOWED_MODELS      (secret) — comma-separated model ids this proxy will run.
 *                                  Not actually secret; stored as one so `npm run
 *                                  sync` can update it without a redeploy.
 *   ALLOWED_ORIGINS     (var)    — comma-separated site origins allowed via CORS,
 *                                  e.g. "https://butter-money.github.io".
 *
 * Why ALLOWED_MODELS exists: provider API keys are account-wide — a console key
 * cannot be scoped to one model. So the only place a model restriction can live
 * is here. Without it, anyone holding the access password could send any model id
 * (including a far more expensive one) and bill it to these keys.
 *
 * Upstreams, all password-gated (keep in sync with lib/audit-client.ts):
 *   POST /v1/messages                 → api.anthropic.com      (Claude models)
 *   POST /google/v1/chat/completions  → generativelanguage…    (Gemini direct)
 *   POST /openai/v1/chat/completions  → api.openai.com         (OpenAI direct)
 */

const ANTHROPIC_URL = 'https://api.anthropic.com';
const GEMINI_URL = 'https://generativelanguage.googleapis.com';
const OPENAI_URL = 'https://api.openai.com';

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const allowOrigin = resolveOrigin(origin, env);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors(allowOrigin) });
    }
    if (request.method !== 'POST') {
      return json({ error: { message: 'Method not allowed.' } }, 405, allowOrigin);
    }

    if (!env.ACCESS_PASSWORD) {
      return json(
        { error: { message: 'Proxy not configured: set ACCESS_PASSWORD.' } },
        500,
        allowOrigin
      );
    }

    // Access gate — constant-time-ish comparison of the shared password.
    const provided = request.headers.get('x-access-password') || '';
    if (!safeEqual(provided, env.ACCESS_PASSWORD)) {
      return json(
        { error: { message: 'Invalid or missing access password.' } },
        401,
        allowOrigin
      );
    }

    // Read the body once so the model can be checked before anything is spent.
    // Every upstream here takes `model` at the top level of the JSON payload.
    const raw = await request.text();
    let payload;
    try {
      payload = JSON.parse(raw);
    } catch {
      return json({ error: { message: 'Body is not valid JSON.' } }, 400, allowOrigin);
    }

    const allowedModels = (env.ALLOWED_MODELS || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (allowedModels.length && !allowedModels.includes(payload.model)) {
      return json(
        {
          error: {
            message: `Model "${payload.model}" is not enabled on this proxy. Enabled: ${allowedModels.join(', ')}.`,
          },
        },
        403,
        allowOrigin
      );
    }

    const url = new URL(request.url);

    // Route by path to the matching upstream, injecting that provider's key.
    // The provider-prefixed paths are checked first (more specific).
    let upstream;
    if (url.pathname.endsWith('/google/v1/chat/completions')) {
      if (!env.GEMINI_API_KEY) {
        return json({ error: { message: 'GEMINI_API_KEY not set on the proxy.' } }, 500, allowOrigin);
      }
      upstream = await fetch(`${GEMINI_URL}/v1beta/openai/chat/completions`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          authorization: `Bearer ${env.GEMINI_API_KEY}`,
        },
        body: raw,
      });
    } else if (url.pathname.endsWith('/openai/v1/chat/completions')) {
      if (!env.OPENAI_API_KEY) {
        return json({ error: { message: 'OPENAI_API_KEY not set on the proxy.' } }, 500, allowOrigin);
      }
      upstream = await fetch(`${OPENAI_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          authorization: `Bearer ${env.OPENAI_API_KEY}`,
        },
        body: raw,
      });
    } else if (url.pathname.endsWith('/v1/messages')) {
      if (!env.ANTHROPIC_API_KEY) {
        return json({ error: { message: 'ANTHROPIC_API_KEY not set on the proxy.' } }, 500, allowOrigin);
      }
      upstream = await fetch(`${ANTHROPIC_URL}/v1/messages`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': env.ANTHROPIC_API_KEY,
          'anthropic-version': request.headers.get('anthropic-version') || '2023-06-01',
          ...(request.headers.get('anthropic-beta')
            ? { 'anthropic-beta': request.headers.get('anthropic-beta') }
            : {}),
        },
        body: raw,
      });
    } else {
      return json({ error: { message: 'Not found.' } }, 404, allowOrigin);
    }

    const headers = cors(allowOrigin);
    headers.set(
      'content-type',
      upstream.headers.get('content-type') || 'application/json'
    );
    return new Response(upstream.body, { status: upstream.status, headers });
  },
};

function resolveOrigin(origin, env) {
  const list = (env.ALLOWED_ORIGINS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  if (list.length === 0) return origin || '*'; // permissive if unset (set it in prod)
  return list.includes(origin) ? origin : list[0];
}

function cors(allowOrigin) {
  return new Headers({
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers':
      'content-type, x-access-password, x-api-key, anthropic-version, anthropic-beta, anthropic-dangerous-direct-browser-access',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  });
}

function json(obj, status, allowOrigin) {
  const headers = cors(allowOrigin);
  headers.set('content-type', 'application/json');
  return new Response(JSON.stringify(obj), { status, headers });
}

function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length)
    return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
