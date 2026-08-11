import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'RegSpine — SEBI compliance, automated and cited',
  description:
    "RegSpine turns SEBI's regulatory text into automated, cited, actionable compliance. Module B audits investor-facing interfaces and communications against SEBI investor-protection norms — mandated risk disclosures, advertising and registration identity, dark patterns, consent and grievance routes — with the cited rule, the exact fix, and a CX upside for every gap.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
