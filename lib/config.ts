import app from '@/app.config.json';
import modelConfig from '@/config/models.public.json';

/**
 * App configuration, read at build time from two files:
 *   - config/models.public.json — the model list (generated, keys stripped)
 *   - app.config.json           — app settings (upload limit, proxy URL)
 *
 * SECURITY: no API key is ever read here, and none can be. RegSpine is a static
 * site, so anything imported into it ships to every visitor's browser. The keys
 * live in config/models.json (git-ignored) and `npm run sync` pushes them into
 * the proxy Worker, writing the key-free .public.json that this file imports.
 * The browser reaches a key only through the password-gated proxy (see worker/).
 */

export interface ModelOption {
  /** The provider's model id, sent to the API. */
  id: string;
  /** Display name in the dropdown. */
  label: string;
  /** Which upstream the proxy routes to: anthropic | google | openai. */
  provider: string;
  /** false = listed but shown as "Unavailable today" and not runnable. Default true. */
  available?: boolean;
  /** Comma-separated artifact types this model can read, e.g. "png,jpeg,webp,gif,pdf". */
  artifacts: string;
}

export interface AppConfig {
  models: ModelOption[];
  defaultModel: string;
  maxTotalMB: number;
  /** Proxy holding the keys server-side. RegSpine always runs through it. */
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

// ------------------------------------------------------------- artifact types

/** The artifact tokens used in config/models.json, mapped to MIME + a display name. */
const ARTIFACT_TYPES: Record<string, { mime: string; label: string }> = {
  png: { mime: 'image/png', label: 'PNG' },
  jpeg: { mime: 'image/jpeg', label: 'JPEG' },
  jpg: { mime: 'image/jpeg', label: 'JPEG' },
  webp: { mime: 'image/webp', label: 'WebP' },
  gif: { mime: 'image/gif', label: 'GIF' },
  pdf: { mime: 'application/pdf', label: 'PDF' },
};

function tokensFor(modelId: string): string[] {
  const raw = CONFIG.models.find((m) => m.id === modelId)?.artifacts || '';
  return raw
    .split(',')
    .map((t) => t.trim().toLowerCase())
    .filter((t) => t in ARTIFACT_TYPES);
}

/** MIME types this model accepts. */
export function mimeTypesFor(modelId: string): string[] {
  return [...new Set(tokensFor(modelId).map((t) => ARTIFACT_TYPES[t].mime))];
}

/** Value for the file input's `accept` attribute, so the picker filters correctly. */
export function acceptFor(modelId: string): string {
  return mimeTypesFor(modelId).join(',');
}

/** Human list of accepted types, e.g. "PNG · JPEG · WebP · GIF". */
export function artifactLabelsFor(modelId: string, sep = ' · '): string {
  return [...new Set(tokensFor(modelId).map((t) => ARTIFACT_TYPES[t].label))].join(sep);
}

export function acceptsType(modelId: string, mime: string): boolean {
  return mimeTypesFor(modelId).includes(mime);
}

/** Available models that can read this MIME type — used to suggest an alternative. */
export function modelsAccepting(mime: string): ModelOption[] {
  return CONFIG.models.filter((m) => m.available !== false && acceptsType(m.id, mime));
}

export function labelForMime(mime: string): string {
  return (
    Object.values(ARTIFACT_TYPES).find((a) => a.mime === mime)?.label || mime
  );
}
