import app from '@/app.config.json';
import modelConfig from '@/config/models.json';

/**
 * App configuration, read at build time from two files:
 *   - config/models.json — the model list + default (safe, committed)
 *   - app.config.json     — app settings (upload limit, proxy URL)
 *
 * SECURITY: no API key is ever read here. RegSpine is a static site, so anything
 * imported into it ships to every visitor's browser. Keys live in config/keys.json
 * (git-ignored) and are pushed to the proxy Worker via `npm run sync-secrets`; the
 * browser reaches them only through the password-gated proxy (see worker/).
 */

export interface ModelOption {
  id: string;
  label: string;
  provider: string;
  /** false = listed but shown as "Unavailable today" and not runnable. Default true. */
  available?: boolean;
}

export interface AppConfig {
  models: ModelOption[];
  defaultModel: string;
  maxTotalMB: number;
  /** Proxy that holds the shared keys server-side; empty = bring-your-own-key. */
  proxy: { url: string; enabled: boolean };
}

const proxyUrl = (app.proxyUrl || '').trim().replace(/\/+$/, '');

export const CONFIG: AppConfig = {
  models: modelConfig.models,
  defaultModel: modelConfig.defaultModel,
  maxTotalMB: app.maxTotalMB,
  proxy: { url: proxyUrl, enabled: proxyUrl.length > 0 },
};

export function isKnownModel(id: string): boolean {
  return CONFIG.models.some((m) => m.id === id);
}

/** Only Claude accepts PDF input; the OpenAI-compatible providers are images-only. */
export function supportsPdf(id: string): boolean {
  return CONFIG.models.find((m) => m.id === id)?.provider === 'anthropic';
}
