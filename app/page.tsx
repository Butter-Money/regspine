'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Scorecard from '@/components/Scorecard';
import TopBar from '@/components/TopBar';
import type { AuditResult } from '@/lib/tool-schema';
import {
  CONFIG,
  acceptFor,
  acceptsType,
  artifactLabelsFor,
  labelForMime,
  modelsAccepting,
} from '@/lib/config';
// Statically imported (not a lazy import()) so it's bundled into the page and
// there's no separate on-demand chunk. A lazy chunk can 404 when a user's tab
// holds stale HTML across a deploy (ChunkLoadError); bundling avoids that.
import { runAudit } from '@/lib/audit-client';

const DEFAULT_MODEL = CONFIG.defaultModel;

// Every model runs through the proxy, so the whole list is always shown; the
// `available` flag in config/models.json decides what's runnable.
const VISIBLE_MODELS = CONFIG.models;

const isAvailable = (id: string) =>
  CONFIG.models.find((m) => m.id === id)?.available !== false;

// Default to the configured model if it's usable, else the first available one.
const DEFAULT_VISIBLE_MODEL =
  (VISIBLE_MODELS.find((m) => m.id === DEFAULT_MODEL && isAvailable(m.id))?.id) ||
  VISIBLE_MODELS.find((m) => isAvailable(m.id))?.id ||
  VISIBLE_MODELS[0]?.id ||
  DEFAULT_MODEL;

interface PickedFile {
  file: File;
  preview?: string; // object URL for images
}

const MAX_TOTAL_MB = CONFIG.maxTotalMB;
const SECRET_STORAGE = 'regspine.secret';
const MODEL_STORAGE = 'regspine.model';

// The only credential a user ever enters. API keys live on the proxy; there is
// no bring-your-own-key path, so nobody is ever asked for one.
const SECRET_UI = {
  chipOn: 'Access set',
  chipOff: 'Add access',
  label: 'Access password',
  help: (
    <>
      RegSpine runs on keys held server-side by its proxy — you never need an API
      key of your own. Enter the <strong>access password</strong> you were given.
      It&apos;s stored only in this browser.
    </>
  ),
  placeholder: 'access password',
  inputType: 'password' as const,
};

// Securities is RegSpine's primary journey; the rest of the rulebook library is
// retained so the same auditor covers Butter Money's lending surfaces too.
const JOURNEYS = [
  {
    value: 'Securities / broker & adviser app (onboarding, trade, advice, grievance)',
    label: 'Securities / broker & adviser app',
  },
  { value: 'auto', label: 'Auto-detect from the artifact' },
  { value: 'Loan onboarding / offer / sanction / disbursal', label: 'Loan journey' },
  { value: 'Embedded insurance attach', label: 'Embedded insurance' },
  { value: 'Data consent / permissions / privacy', label: 'Consent / DPDP' },
  { value: 'Complaint / grievance / support', label: 'Grievance / support' },
];

const DEFAULT_JOURNEY = JOURNEYS[0].value;

const LOADING_STEPS = [
  'Reading the artifact…',
  'Classifying the journey & loading rulebooks…',
  'Auditing at flow, screen & component level…',
  'Running the banned-pattern checklist…',
  'Building the scorecard…',
];

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function fileToBase64(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const res = reader.result as string;
      resolve(res.split(',')[1] ?? '');
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Vision models cap image resolution internally (~1500px), and a multi-MB image
// makes the API call slow enough to hit gateway timeouts. Downscale large images
// to a sane max before sending — big latency/size win, no loss of detail the
// model would have used anyway. PDFs pass through as-is.
const MAX_IMAGE_DIM = 1600;
const DOWNSCALE_ABOVE_BYTES = 900 * 1024; // leave small images untouched

async function encodeForUpload(
  file: File
): Promise<{ name: string; type: string; data: string }> {
  const passthrough = async () => ({
    name: file.name,
    type: file.type,
    data: await fileToBase64(file),
  });

  if (!file.type.startsWith('image/') || file.type === 'image/gif') {
    return passthrough(); // PDFs and animated GIFs untouched
  }
  if (file.size <= DOWNSCALE_ABOVE_BYTES) return passthrough();

  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_IMAGE_DIM / Math.max(bitmap.width, bitmap.height));
    const w = Math.max(1, Math.round(bitmap.width * scale));
    const h = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return passthrough();
    ctx.drawImage(bitmap, 0, 0, w, h);
    bitmap.close?.();
    const blob: Blob | null = await new Promise((res) =>
      canvas.toBlob((b) => res(b), 'image/jpeg', 0.85)
    );
    if (!blob) return passthrough();
    return { name: file.name, type: 'image/jpeg', data: await fileToBase64(blob) };
  } catch {
    return passthrough(); // any failure → send the original
  }
}

export default function Home() {
  const [files, setFiles] = useState<PickedFile[]>([]);
  const [description, setDescription] = useState('');
  const [journey, setJourney] = useState(DEFAULT_JOURNEY);
  const [model, setModel] = useState(DEFAULT_VISIBLE_MODEL);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AuditResult | null>(null);
  const [usedModel, setUsedModel] = useState<string | undefined>();
  const [drag, setDrag] = useState(false);

  const [secret, setSecret] = useState('');
  const [showKeyPanel, setShowKeyPanel] = useState(false);
  const [secretSaved, setSecretSaved] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const stepTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Restore the saved secret/model.
  useEffect(() => {
    const storedSecret = localStorage.getItem(SECRET_STORAGE) || '';
    const storedModel = localStorage.getItem(MODEL_STORAGE) || DEFAULT_MODEL;
    setSecret(storedSecret);
    setModel(
      VISIBLE_MODELS.some((m) => m.id === storedModel) && isAvailable(storedModel)
        ? storedModel
        : DEFAULT_VISIBLE_MODEL
    );
    setSecretSaved(!!storedSecret);
    if (!storedSecret) setShowKeyPanel(true);
  }, []);

  function saveSecret() {
    localStorage.setItem(SECRET_STORAGE, secret.trim());
    setSecretSaved(!!secret.trim());
    setShowKeyPanel(false);
    setError(null);
  }

  function clearSecret() {
    localStorage.removeItem(SECRET_STORAGE);
    setSecret('');
    setSecretSaved(false);
    setShowKeyPanel(true);
  }

  function onModelChange(id: string) {
    setModel(id);
    localStorage.setItem(MODEL_STORAGE, id);
  }

  // What counts as a valid artifact depends on the selected model — it's declared
  // per model in config/models.json, not hard-coded here.
  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      setError(null);
      const accepted: PickedFile[] = [];
      for (const file of Array.from(incoming)) {
        if (!acceptsType(model, file.type)) {
          const alt = modelsAccepting(file.type)[0];
          setError(
            `"${file.name}" is a ${labelForMime(file.type)} file, which ${
              CONFIG.models.find((m) => m.id === model)?.label.split(' — ')[0] ||
              'this model'
            } can't read — skipped.${
              alt ? ` ${alt.label.split(' — ')[0]} can.` : ''
            }`
          );
          continue;
        }
        accepted.push({
          file,
          preview: file.type.startsWith('image/')
            ? URL.createObjectURL(file)
            : undefined,
        });
      }
      setFiles((prev) => [...prev, ...accepted]);
    },
    [model]
  );

  function removeFile(idx: number) {
    setFiles((prev) => {
      const next = [...prev];
      const [removed] = next.splice(idx, 1);
      if (removed?.preview) URL.revokeObjectURL(removed.preview);
      return next;
    });
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDrag(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  }

  async function handleRun() {
    setError(null);

    if (!isAvailable(model)) {
      const cur = CONFIG.models.find((m) => m.id === model);
      const alt = VISIBLE_MODELS.find((m) => isAvailable(m.id));
      setError(
        `${(cur?.label || model).split(' — ')[0]} is unavailable today. Pick another model${
          alt ? ` (e.g. ${alt.label.split(' — ')[0]})` : ''
        }.`
      );
      return;
    }

    const s = secret.trim();
    if (!s) {
      setShowKeyPanel(true);
      setError('Enter the access password first — it stays in your browser.');
      return;
    }
    const totalBytes = files.reduce((acc, f) => acc + f.file.size, 0);
    if (totalBytes > MAX_TOTAL_MB * 1024 * 1024) {
      setError(
        `Attachments total ${fmtSize(totalBytes)} — keep under ${MAX_TOTAL_MB} MB. Remove or compress some files.`
      );
      return;
    }
    if (files.length === 0 && !description.trim()) {
      setError('Attach at least one screenshot/PDF or paste a flow description.');
      return;
    }
    // The model may have been switched after the files were picked.
    const unsupported = files.find((f) => !acceptsType(model, f.file.type));
    if (unsupported) {
      const alt = modelsAccepting(unsupported.file.type)[0];
      setError(
        `This model can't read ${labelForMime(unsupported.file.type)} files ("${unsupported.file.name}").${
          alt ? ` Switch to ${alt.label.split(' — ')[0]}, or remove the file.` : ' Remove the file.'
        }`
      );
      return;
    }

    setLoading(true);
    setLoadingStep(0);
    stepTimer.current = setInterval(() => {
      setLoadingStep((step) => Math.min(step + 1, LOADING_STEPS.length - 1));
    }, 9000);

    try {
      const encoded = await Promise.all(files.map((f) => encodeForUpload(f.file)));

      const { result: audit, model: usedM } = await runAudit({
        secret: s,
        model,
        description,
        journeyHint: journey,
        files: encoded,
      });
      setResult(audit);
      setUsedModel(usedM);
    } catch (e) {
      setError(humaniseError(e));
    } finally {
      if (stepTimer.current) clearInterval(stepTimer.current);
      setLoading(false);
    }
  }

  function reset() {
    files.forEach((f) => f.preview && URL.revokeObjectURL(f.preview));
    setFiles([]);
    setDescription('');
    setJourney(DEFAULT_JOURNEY);
    setResult(null);
    setError(null);
    setUsedModel(undefined);
  }

  return (
    <>
      <TopBar
        active="B"
        secret={{
          saved: secretSaved,
          labelOn: SECRET_UI.chipOn,
          labelOff: SECRET_UI.chipOff,
          title: SECRET_UI.label,
          onClick: () => setShowKeyPanel((v) => !v),
        }}
      />

      <div className="wrap">
        <div className="page-head">
          <span className="module-chip">
            RegSpine · Module <span className="b">B</span> — Interface &amp;
            Communication Auditor
          </span>
          <h1 style={{ marginTop: 14 }}>
            Audit an investor-facing screen against{' '}
            <span className="accent">SEBI</span>
          </h1>
        </div>
        <p className="tagline">
          Upload a broker or investment-adviser screen (or a PDF, or describe the
          flow) and get a scored, cited compliance report — mandated risk
          disclosures, advertising and SEBI registration identity, suitability and
          fee transparency, order-cost disclosure, consent and the SCORES/ODR
          grievance route — with the exact fix and a CX upside for every gap.
        </p>

        {showKeyPanel && (
          <div className="card key-panel">
            <label className="field-label">{SECRET_UI.label}</label>
            <p className="key-help">{SECRET_UI.help}</p>
            <input
              className="key-input"
              type={SECRET_UI.inputType}
              placeholder={SECRET_UI.placeholder}
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
            <div className="row" style={{ marginTop: 14 }}>
              <button className="submit-btn" onClick={saveSecret}>
                Save
              </button>
              {secretSaved && (
                <button className="ghost-btn" onClick={clearSecret}>
                  Remove
                </button>
              )}
            </div>
          </div>
        )}

        {loading ? (
          <div className="card">
            <div className="loading">
              <div className="spinner" />
              <div>{LOADING_STEPS[loadingStep]}</div>
              <div className="steps">
                Running the full rulebook audit — this usually takes 20–60 seconds.
              </div>
            </div>
          </div>
        ) : result ? (
          <Scorecard result={result} model={usedModel} onReset={reset} />
        ) : (
          <div className="card">
            <label className="field-label">Artifact</label>
            <div
              className={`dropzone${drag ? ' drag' : ''}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={onDrop}
            >
              <div className="big">
                Drop a screen{acceptsType(model, 'application/pdf') ? ' or PDF' : ''} here,
                or click to browse
              </div>
              <div className="small">
                {artifactLabelsFor(model)} — up to {MAX_TOTAL_MB} MB total
              </div>
              <input
                ref={inputRef}
                type="file"
                accept={acceptFor(model)}
                multiple
                hidden
                onChange={(e) => e.target.files && addFiles(e.target.files)}
              />
            </div>

            {files.length > 0 && (
              <ul className="file-list">
                {files.map((f, i) => (
                  <li className="file-item" key={i}>
                    {f.preview ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img className="thumb" src={f.preview} alt="" />
                    ) : (
                      <span className="doc-badge">PDF</span>
                    )}
                    <span className="fname">{f.file.name}</span>
                    <span className="fsize">{fmtSize(f.file.size)}</span>
                    <button onClick={() => removeFile(i)} title="Remove">
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <div style={{ marginTop: 22 }}>
              <label className="field-label">
                Flow description / context{' '}
                <span
                  style={{
                    textTransform: 'none',
                    color: 'var(--text-faint)',
                    fontWeight: 400,
                  }}
                >
                  (optional if you attached screens — required if you didn&apos;t)
                </span>
              </label>
              <textarea
                placeholder="e.g. Account-opening screen for a discount broker. The F&O segment toggle is on by default; the 'Add advisory pack' checkbox is pre-ticked. The nomination step has 'Add nominee' as a filled button and the opt-out as a small grey text link…"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="row" style={{ marginTop: 22 }}>
              <div className="grow">
                <label className="field-label">Primary journey</label>
                <select value={journey} onChange={(e) => setJourney(e.target.value)}>
                  {JOURNEYS.map((j) => (
                    <option key={j.value} value={j.value}>
                      {j.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grow">
                <label className="field-label">
                  Model
                  <span className={`model-status ${isAvailable(model) ? 'ok' : 'bad'}`}>
                    <span className="status-dot" />
                    {isAvailable(model) ? 'Available' : 'Unavailable today'}
                  </span>
                </label>
                <select value={model} onChange={(e) => onModelChange(e.target.value)}>
                  {VISIBLE_MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label} ({artifactLabelsFor(m.id, ', ')})
                      {m.available === false ? ' — unavailable' : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="row" style={{ marginTop: 18, justifyContent: 'flex-end' }}>
              <button
                className="submit-btn"
                onClick={handleRun}
                disabled={!isAvailable(model)}
                title={isAvailable(model) ? '' : 'This model is unavailable today'}
              >
                Run compliance audit →
              </button>
            </div>

            <p className="hint">
              The banned-pattern checklist — 12 cross-sector patterns plus the 3 SEBI
              securities additions — runs on every audit regardless of journey.
              Screenshots give the most accurate component-level findings (CTA
              weights, pre-ticked boxes, where a disclosure actually sits);
              text-only reviews flag what can&apos;t be visually confirmed.
            </p>

            {error && <div className="error-banner">{error}</div>}
          </div>
        )}

        {!result && !loading && (
          <p className="footer-note">
            Module B runs the <code>regspine-audit</code> rulebooks in your browser
            via the RegSpine key proxy. Every audit is a live model call on the
            artifact you upload — nothing is cached or pre-computed. Informs design
            and compliance decisions — not legal sign-off.
          </p>
        )}
      </div>
    </>
  );
}

function humaniseError(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e);
  if (/access password/i.test(msg))
    return 'The access password was rejected. Check it in settings (the chip at the top right).';
  if (/401|authentication|invalid x-api-key|invalid_api_key/i.test(msg))
    return 'The proxy rejected the request (401). Check the access password in settings.';
  if (/429|rate limit|overloaded/i.test(msg))
    return 'The model provider is rate-limiting or overloaded (429). Wait a moment and retry.';
  if (/not set on the proxy/i.test(msg))
    // The proxy is telling us which provider key is missing — pass it through.
    return `${msg} Pick a model whose provider has a key loaded, or add the key in config/models.json and run \`npm run sync\`.`;
  if (/insufficient credits|credit balance|billing|402|quota/i.test(msg))
    return `The provider account for this model is out of credit or quota. Top it up, or switch models. (${msg})`;
  if (/Failed to fetch|NetworkError|CORS/i.test(msg))
    return 'Network/CORS error reaching the proxy. Confirm the proxy URL and that this site origin is allowed.';
  return msg;
}
