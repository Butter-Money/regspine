'use client';

import Link from 'next/link';

/**
 * Shared top bar. Carries the RegSpine wordmark, the module switcher (the two
 * halves of the platform), and — on Module B — the credential chip.
 */
export default function TopBar({
  active,
  secret,
}: {
  active: 'B' | 'A';
  secret?: {
    saved: boolean;
    labelOn: string;
    labelOff: string;
    title: string;
    onClick: () => void;
  };
}) {
  return (
    <div className="topbar">
      <div className="topbar-inner">
        <Link className="wordmark" href="/">
          <span className="mark">◗</span>
          RegSpine<span className="dot">.</span>
        </Link>

        <nav className="module-nav">
          <Link href="/" className={active === 'B' ? 'active' : undefined}>
            Module B<span className="tag">Auditor</span>
          </Link>
          <Link
            href="/obligations/"
            className={active === 'A' ? 'active' : undefined}
          >
            Module A<span className="tag">Obligation Engine</span>
          </Link>
        </nav>

        <div className="spacer" />

        <nav className="nav-links">
          <a href="https://www.butter.money" target="_blank" rel="noreferrer">
            Butter Money ↗
          </a>
        </nav>

        {secret && (
          <button className="key-chip" onClick={secret.onClick} title={secret.title}>
            <span className={`key-dot ${secret.saved ? 'on' : 'off'}`} />
            {secret.saved ? secret.labelOn : secret.labelOff}
          </button>
        )}
      </div>
    </div>
  );
}
