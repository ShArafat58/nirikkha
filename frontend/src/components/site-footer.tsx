// Footer generated with Lovable: https://lovable.dev/projects/ed9baf51-2e9f-4aeb-9ac6-9d7558b663fc
// Used as generated; the parent passes Bengali labels.
// SiteFooter — footer for Nirikkha (নিরীক্ষা), Governance Crash-Test AI.
// Theme tokens: bg-bg, bg-surface, text-text, text-muted, text-accent,
// border-border, border-accent. No hex colours, no external UI/icon
// libraries, inline SVG only.

export interface SiteFooterLabels {
  productName: string;
  tagline: string;
  builtLine: string;
  productHeading: string;
  learnHeading: string;
  responsibleHeading: string;
  responsibleText: string;
  copyright: string;
  evidenceLine: string;
  productNavLabel: string;
  learnNavLabel: string;
  githubLinkLabel: string;
  links: {
    crashTest: string;
    reports: string;
    replay: string;
    graph: string;
    radar: string;
    pricing: string;
    docs: string;
    github: string;
  };
}

const DEFAULT_LABELS: SiteFooterLabels = {
  productName: "Nirikkha",
  tagline: "Trust less, Verify more.",
  builtLine:
    "Built for the GovernanceIQ challenge, International AI Builders Congress 2026.",
  productHeading: "Product",
  learnHeading: "Learn",
  responsibleHeading: "Responsible use",
  responsibleText:
    "Nirikkha does not accuse any company. Findings are questions to verify, not proof. Not legal or investment advice.",
  copyright: "© 2026 Nirikkha",
  evidenceLine: "Public SEC filings only · Evidence first",
  productNavLabel: "Product links",
  learnNavLabel: "Learn links",
  githubLinkLabel: "Nirikkha on GitHub (opens in a new tab)",
  links: {
    crashTest: "Crash-Test",
    reports: "Reports",
    replay: "Replay",
    graph: "Graph",
    radar: "Radar",
    pricing: "Pricing",
    docs: "Docs",
    github: "GitHub",
  },
};

const productLinks = (l: SiteFooterLabels): { label: string; href: string; external?: boolean }[] => [
  { label: l.links.crashTest, href: "/crash-test" },
  { label: l.links.reports, href: "/reports" },
  { label: l.links.replay, href: "/replay" },
  { label: l.links.graph, href: "/graph" },
  { label: l.links.radar, href: "/radar" },
];

const learnLinks = (l: SiteFooterLabels): { label: string; href: string; external?: boolean }[] => [
  { label: l.links.pricing, href: "/pricing" },
  { label: l.links.docs, href: "/docs" },
];

const footerLinkClass =
  "text-muted transition-colors hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

const footerHeadingClass =
  "text-sm font-semibold uppercase tracking-wider text-text";

function LogoMark() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="text-accent"
    >
      <circle cx="10.5" cy="10.5" r="6.5" />
      <line x1="15.4" y1="15.4" x2="21" y2="21" />
    </svg>
  );
}

export default function SiteFooter({
  labels = DEFAULT_LABELS,
}: {
  labels?: Partial<SiteFooterLabels>;
}) {
  const l: SiteFooterLabels = { ...DEFAULT_LABELS, ...labels };

  return (
    <footer className="border-t border-border bg-bg text-text">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-4">
          {/* Column 1: brand */}
          <div>
            <div className="flex items-center gap-3">
              <LogoMark />
              <span className="text-lg font-bold">{l.productName}</span>
            </div>
            <p className="mt-3 text-sm font-medium text-accent">{l.tagline}</p>
            <p className="mt-3 text-xs leading-relaxed text-muted">
              {l.builtLine}
            </p>
          </div>

          {/* Column 2: Product */}
          <nav aria-label={l.productNavLabel}>
            <h2 className={footerHeadingClass}>{l.productHeading}</h2>
            <ul className="mt-4 space-y-3">
              {productLinks(l).map((link) => (
                <li key={link.href}>
                  <a href={link.href} className={`text-sm ${footerLinkClass}`}>
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          {/* Column 3: Learn */}
          <nav aria-label={l.learnNavLabel}>
            <h2 className={footerHeadingClass}>{l.learnHeading}</h2>
            <ul className="mt-4 space-y-3">
              {learnLinks(l).map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className={`text-sm ${footerLinkClass}`}
                    {...(link.external
                      ? {
                          target: "_blank",
                          rel: "noopener noreferrer",
                          "aria-label": l.githubLinkLabel,
                        }
                      : {})}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          {/* Column 4: Responsible use */}
          <div>
            <h2 className={footerHeadingClass}>{l.responsibleHeading}</h2>
            <p className="mt-4 text-sm leading-relaxed text-muted">
              {l.responsibleText}
            </p>
          </div>
        </div>

        {/* Bottom row */}
        <div className="mt-12 flex flex-col gap-2 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted">{l.copyright}</p>
          <p className="text-xs text-muted">{l.evidenceLine}</p>
        </div>
      </div>
    </footer>
  );
}
