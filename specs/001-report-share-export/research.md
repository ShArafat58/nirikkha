# Research: Report Sharing and Export

**Feature**: `001-report-share-export`
**Phase**: Phase 0

## Research Decisions

### 1. Clipboard Copy Mechanism
- **Decision**: Use `navigator.clipboard.writeText(url)` with fallback handling for unsecure contexts or unsupported environments.
- **Rationale**: `navigator.clipboard` is the modern, standard asynchronous web API supported across all modern evergreen desktop and mobile browsers. Fallback creates a temporary non-rendered textarea to execute `document.execCommand('copy')` if `navigator.clipboard` is undefined or rejects.
- **Alternatives Considered**: External clipboard libraries (e.g. `copy-to-clipboard`). Rejected because Nirikkha avoids unnecessary third-party npm dependencies on the free stack.

### 2. JSON Export Generation & Trigger
- **Decision**: Serialize the existing in-memory `job.report` object using `JSON.stringify(report, null, 2)` inside a `Blob` of type `application/json`, create an object URL with `URL.createObjectURL(blob)`, append a hidden `<a>` element with `download="nirikkha-report-${id}.json"`, invoke `.click()`, and revoke the object URL.
- **Rationale**: Completely client-side, zero latency, zero backend overhead, works in offline/mock mode. Ensures the exact in-memory findings, citations, and scores displayed on screen are archived.
- **Alternatives Considered**: Fetching a dedicated export endpoint from the backend (e.g. `GET /api/crash-tests/{id}/export`). Rejected because AGENTS.md rule 1 & user prompt specify "No backend changes", and the frontend already possesses the complete canonical report object.

### 3. Share Confirmation & Access Policy Disclosure
- **Decision**: Display an inline transient banner or toast notification under the action bar that indicates copy success and explains access rules:
  - Featured demo report (`job.source === 'featured' || job.source === 'demo' || (job as any).featured || job.report?.featured`): informs user that the link is public and anyone can view it without logging in.
  - Custom / private report: informs user that viewers must sign in to view this report.
  The notification automatically clears after 3.5 seconds.
- **Rationale**: Gives clear, non-intrusive feedback without blocking user navigation. Respects the distinction between public demo reports and authenticated user analyses.
- **Alternatives Considered**: Modal popup dialog. Rejected because copying a URL is a lightweight interaction; a modal adds unnecessary friction.

### 4. Layout, Styling & Print Visibility
- **Decision**: Group "Legal memo", "Copy share link", and "Download JSON" into a responsive flex row (`flex flex-wrap items-center gap-2.5 print:hidden`) in `frontend/src/app/report/[id]/page.tsx` (or a dedicated component `ReportActions`).
- **Rationale**: Matches existing UI aesthetic (neutral/slate borders, subtle hover transitions, rounded corners, inline icons, font styling matching `MemoLink`). Applying `print:hidden` ensures printed memos and PDF exports contain zero interactive action buttons.
- **Alternatives Considered**: Floating action button (FAB) or bottom bar. Rejected because report headers provide standard placement alongside `MemoLink` and navigation links.

### 5. Internationalization (i18n)
- **Decision**: Add dedicated keys to `en` and `bn` dictionaries in `frontend/src/lib/i18n.ts`:
  - `rep.share`: "Share link" / "শেয়ার লিঙ্ক"
  - `rep.shareCopied`: "Link copied to clipboard!" / "লিঙ্ক ক্লিপবোর্ডে কপি করা হয়েছে!"
  - `rep.sharePublicNote`: "Featured reports are public and can be viewed without logging in." / "ফিচার্ড রিপোর্টগুলো উন্মুক্ত এবং লগইন ছাড়াই দেখা যায়।"
  - `rep.shareAuthNote`: "Recipients will need to sign in to Nirikkha to view this report." / "এই রিপোর্ট দেখতে প্রাপকদের নিরীক্ষায় সাইন ইন করতে হবে।"
  - `rep.downloadJson`: "Download JSON" / "JSON ডাউনলোড"
- **Rationale**: Complies strictly with Principle VI in Nirikkha Constitution (dual-language accessibility EN/BN without hardcoded strings).
