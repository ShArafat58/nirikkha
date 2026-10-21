# Implementation Plan: Report Sharing and Export

**Branch**: `001-report-share-export` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-report-share-export/spec.md`

## Summary

Enhance the Crash-Test report page (`frontend/src/app/report/[id]/page.tsx`) by providing two accessible, client-side actions placed directly alongside the "Legal memo" button:
1. **Copy share link**: Copies the absolute canonical report URL to the clipboard with temporary feedback specifying public access (featured demo) versus login requirements (private/custom report).
2. **Download JSON**: Generates and downloads a client-side pretty-printed JSON file named `nirikkha-report-<id>.json` representing the complete audit snapshot of the report.

Both actions are fully keyboard accessible, localized in English and Bengali (EN/BN), styled to blend harmoniously with existing report action controls, and omitted during print (`print:hidden`). Zero backend changes are required.

## Technical Context

**Language/Version**: TypeScript 5+, Next.js 15 (App Router), React 19
**Primary Dependencies**: Tailwind CSS, Web Clipboard API (`navigator.clipboard`), Web Blob API
**Storage**: Client-side in-memory state; browser download trigger (no local storage persistence needed)
**Testing**: Production build validation (`npm run build`), manual quickstart acceptance test
**Target Platform**: Evergreen desktop & mobile web browsers, print media stylesheet
**Project Type**: Web application UI feature (Frontend only)
**Performance Goals**: Instant clipboard copy (<50ms), instant client-side download generation (<100ms)
**Constraints**: Zero backend changes; no external npm dependencies; print hidden (`print:hidden`); full EN/BN i18n
**Scale/Scope**: 1 UI component / page enhancement, 5 new i18n translation keys in EN and BN

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Evaluation | Status |
|---|---|---|
| I. Evidence-First | Report export contains full citations, passages, and filing references unmodified. | PASS |
| II. Responsible Uncertainty | Insufficient evidence badges and scores are preserved verbatim in JSON export. | PASS |
| III. Separation of Severity & Confidence | Data model preserves separate fields for severity and confidence. | PASS |
| IV. Non-Accusatory Governance Language | User-facing copy uses objective, neutral governance terminology. | PASS |
| V. Domain Separation | Export maintains separation between law, best practices, and internal indicators. | PASS |
| Hard Rule 1: Frontend/Backend Isolation | Pure client-side implementation. Zero backend changes; no code shared. | PASS |
| Hard Rule 5: 100% Free Stack | Uses native browser Web APIs; zero paid SDKs or new dependencies. | PASS |
| Dual-Language Accessibility (EN/BN) | All button labels and toast notifications localized in both English and Bengali. | PASS |
| Print Media Standard | All interactive export/share controls hidden during printing (`print:hidden`). | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/001-report-share-export/
├── plan.md              # Implementation Plan
├── research.md          # Technical research & decisions (Phase 0)
├── data-model.md        # Export data model & transient UI state (Phase 1)
├── quickstart.md        # Validation scenarios & test steps (Phase 1)
├── contracts/
│   └── report-actions.md # Component props & interaction contract
├── checklists/
│   └── requirements.md  # Spec quality validation checklist
└── tasks.md             # Implementation tasks (Phase 2 output)
```

### Source Code Layout

```text
frontend/
├── src/
│   ├── app/
│   │   └── report/
│   │       └── [id]/
│   │           └── page.tsx            # Report page integrating report actions
│   ├── components/
│   │   └── report/
│   │       ├── memo-link.tsx           # Existing memo link component
│   │       └── report-actions.tsx      # Share link & JSON export action bar
│   └── lib/
│       └── i18n.ts                     # EN and BN translation dictionaries
```

**Structure Decision**: Created a modular `ReportActions` component in `frontend/src/components/report/report-actions.tsx` to encapsulate copy logic, transient toast dismissals, and download triggers cleanly, then rendered next to `MemoLink` in `frontend/src/app/report/[id]/page.tsx`.

## Complexity Tracking

*No violations. Clean frontend-only enhancement.*
