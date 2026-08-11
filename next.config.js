/** @type {import('next').NextConfig} */

// GitHub Pages can serve this either at a repo subpath (public project site,
// https://<org>.github.io/<repo>/) or at the root of a randomized subdomain
// (Enterprise private site, https://<id>.pages.github.io/). The deploy workflow
// passes the correct value in PAGES_BASE_PATH via actions/configure-pages; we
// normalise it to a Next basePath ("" for root, "/<repo>" for a subpath).
// Local dev/build stay at root.
const isPages = process.env.GITHUB_PAGES === 'true';
let basePath = '';
if (isPages) {
  let raw = process.env.PAGES_BASE_PATH || '';
  // configure-pages may hand back a full origin; keep only the path portion.
  try {
    if (/^https?:\/\//.test(raw)) raw = new URL(raw).pathname;
  } catch {}
  raw = raw.replace(/\/+$/, ''); // strip trailing slash(es)
  basePath = raw === '' || raw === '/' ? '' : raw;
}

const nextConfig = {
  // Fully static build — no server. The audit runs client-side against the
  // Anthropic API with the user's own key. This is what makes it Pages-hostable.
  output: 'export',
  trailingSlash: true,
  basePath,
  assetPrefix: basePath || undefined,
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
};

module.exports = nextConfig;
