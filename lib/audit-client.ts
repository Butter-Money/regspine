import Anthropic from '@anthropic-ai/sdk';
import { SKILL_CONTEXT } from './skill-content';
import { buildSystemPrompt, buildUserContext } from './prompt';
import { AUDIT_TOOL, type AuditResult } from './tool-schema';
import { CONFIG } from './config';

/**
 * Runs the Module B compliance audit from the browser. Provider is chosen per
 * model (see config/models.json):
 *
 *  - "anthropic": native Claude Messages API. Direct with the user's key (BYOK),
 *    or via the shared-key proxy. Handles images AND PDFs.
 *  - "google" / "openai": OpenAI-compatible chat-completions via the proxy Worker,
 *    which injects the matching shared key. Images only — PDFs are Claude-only.
 *
 * The system prompt (the skill + rulebooks) and the forced structured-output
 * schema are identical across providers, so the audit itself doesn't change.
 */

export const DEFAULT_MODEL = CONFIG.defaultModel;

export interface AuditFile {
  name: string;
  type: string; // MIME
  data: string; // base64 (no data: prefix)
}

export interface RunAuditInput {
  /** BYOK: Anthropic API key. Proxy mode: the shared access password. */
  secret: string;
  model?: string;
  description?: string;
  journeyHint?: string;
  files: AuditFile[];
}

const SUPPORTED_IMAGE = ['image/png', 'image/jpeg', 'image/webp', 'image/gif'];

// Provider gateways occasionally return transient overload/timeout statuses on a
// heavy multimodal audit (503/504/429). Retry a couple of times with backoff.
const TRANSIENT = new Set([408, 429, 500, 502, 503, 504, 529]);

// Proxy path per provider. Keep in sync with worker/src/worker.js.
const PROVIDER_PATH: Record<string, string> = {
  google: '/google/v1/chat/completions',
  openai: '/openai/v1/chat/completions',
};

async function fetchWithRetry(
  url: string,
  opts: RequestInit,
  tries = 3
): Promise<Response> {
  let res: Response | null = null;
  for (let i = 0; i < tries; i++) {
    res = await fetch(url, opts);
    if (res.ok || !TRANSIENT.has(res.status)) return res;
    if (i < tries - 1) await new Promise((r) => setTimeout(r, 1500 * (i + 1)));
  }
  return res as Response;
}

function providerFor(modelId: string): string {
  return CONFIG.models.find((m) => m.id === modelId)?.provider || 'anthropic';
}

export async function runAudit(
  input: RunAuditInput
): Promise<{ result: AuditResult; model: string }> {
  const model = input.model?.trim() || DEFAULT_MODEL;
  const provider = providerFor(model);

  const images = input.files.filter((f) => SUPPORTED_IMAGE.includes(f.type));
  const pdfs = input.files.filter((f) => f.type === 'application/pdf');

  const system = buildSystemPrompt(SKILL_CONTEXT);
  const userText = buildUserContext({
    journeyHint: input.journeyHint,
    description: input.description,
    imageCount: images.length,
    pdfCount: pdfs.length,
  });

  const args = { model, secret: input.secret, system, userText, images, pdfs };
  const path = PROVIDER_PATH[provider];
  const result = path
    ? await runViaOpenAICompat({ ...args, path })
    : await runViaAnthropic(args);

  return { result, model };
}

// ---------------------------------------------------------------- Anthropic

interface ProviderArgs {
  model: string;
  secret: string;
  system: string;
  userText: string;
  images: AuditFile[];
  pdfs: AuditFile[];
}

async function runViaAnthropic({
  model,
  secret,
  system,
  userText,
  images,
  pdfs,
}: ProviderArgs): Promise<AuditResult> {
  const client = CONFIG.proxy.enabled
    ? new Anthropic({
        baseURL: CONFIG.proxy.url,
        apiKey: 'proxy',
        dangerouslyAllowBrowser: true,
        defaultHeaders: {
          'x-access-password': secret,
          'anthropic-dangerous-direct-browser-access': 'true',
        },
      })
    : new Anthropic({
        apiKey: secret,
        dangerouslyAllowBrowser: true,
        defaultHeaders: { 'anthropic-dangerous-direct-browser-access': 'true' },
      });

  const content: Anthropic.ContentBlockParam[] = [];
  for (const img of images) {
    content.push({
      type: 'image',
      source: {
        type: 'base64',
        media_type: img.type as 'image/png' | 'image/jpeg' | 'image/webp' | 'image/gif',
        data: img.data,
      },
    });
  }
  for (const pdf of pdfs) {
    content.push({
      type: 'document',
      source: { type: 'base64', media_type: 'application/pdf', data: pdf.data },
    });
  }
  content.push({ type: 'text', text: userText });

  const message = await client.messages.create({
    model,
    max_tokens: 16000,
    system,
    tools: [AUDIT_TOOL],
    tool_choice: { type: 'tool', name: 'submit_audit' },
    messages: [{ role: 'user', content }],
  });

  const toolUse = message.content.find(
    (b): b is Anthropic.ToolUseBlock => b.type === 'tool_use' && b.name === 'submit_audit'
  );
  if (!toolUse) throw new Error('The model did not return a structured audit. Please retry.');
  return toolUse.input as AuditResult;
}

// ------------------------------------------- OpenAI-compatible (Gemini / OpenAI)

// `path` selects the proxy upstream: '/google/v1/chat/completions' → Gemini
// direct, '/openai/v1/chat/completions' → OpenAI. Both speak the OpenAI format.
async function runViaOpenAICompat({
  model,
  secret,
  system,
  userText,
  images,
  pdfs,
  path,
}: ProviderArgs & { path: string }): Promise<AuditResult> {
  if (!CONFIG.proxy.enabled) {
    throw new Error(
      'This model runs through the shared-key proxy, which is not configured. Use a Claude model with your own key, or set up the proxy (see worker/).'
    );
  }
  if (pdfs.length) {
    throw new Error(
      'PDF input is supported only on Claude models. Pick a Claude model, or attach screenshots instead of a PDF for this model.'
    );
  }

  // OpenAI-compatible message with image_url data URIs.
  const userContent: unknown[] = images.map((img) => ({
    type: 'image_url',
    image_url: { url: `data:${img.type};base64,${img.data}` },
  }));
  userContent.push({ type: 'text', text: userText });

  const body = {
    model,
    max_tokens: 16000,
    messages: [
      { role: 'system', content: system },
      { role: 'user', content: userContent },
    ],
    tools: [
      {
        type: 'function',
        function: {
          name: AUDIT_TOOL.name,
          description: AUDIT_TOOL.description,
          parameters: AUDIT_TOOL.input_schema,
        },
      },
    ],
    tool_choice: { type: 'function', function: { name: AUDIT_TOOL.name } },
  };

  const res = await fetchWithRetry(`${CONFIG.proxy.url}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-access-password': secret },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let msg = `Request failed (${res.status}).`;
    try {
      const j = await res.json();
      msg = j?.error?.message || msg;
    } catch {
      /* keep default */
    }
    throw new Error(msg);
  }

  const json = await res.json();
  const call = json?.choices?.[0]?.message?.tool_calls?.[0];
  const args = call?.function?.arguments;
  if (!args) {
    throw new Error(
      'This model did not return a structured audit (no tool call). Try a Claude or Gemini model — some models are unreliable at forced structured output.'
    );
  }
  try {
    return JSON.parse(args) as AuditResult;
  } catch {
    throw new Error('The model returned malformed structured output. Please retry or switch models.');
  }
}
