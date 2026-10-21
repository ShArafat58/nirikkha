# Tasks: Report sharing and export

**Feature**: `001-report-share-export` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Scope**: frontend only, no backend or API changes (constitution: frontend talks to the backend only through the REST API).

Legend: `[P]` can run in parallel · `[US1]` Copy share link · `[US2]` Download JSON

## Phase 1: Setup

- [x] T001 Confirm the existing report API call `getCrashTest(id)` in `frontend/src/lib/api.ts` returns the full report JSON (no new endpoint needed)
- [x] T002 Confirm placement next to `MemoLink` in `frontend/src/app/report/[id]/page.tsx`

## Phase 2: Foundation

- [x] T003 Create `frontend/src/components/report/report-actions.tsx` as a client component using `useParams` for the report id and `useApp()` for EN/BN
- [x] T004 Keep every visible string in an EN/BN table inside the component (constitution: EN/BN for every user-facing string)

## Phase 3: User Story 1 — Copy share link (P1)

- [x] T005 [US1] Button "Copy share link" copies `window.location.origin + /report/<id>` with the Clipboard API, falling back to a hidden textarea when the API is unavailable
- [x] T006 [US1] Show a short confirmation in an `aria-live="polite"` region for 2.5 s; show a clear error text if copying fails
- [x] T007 [US1] Show the note "Featured reports are public. Other reports ask the viewer to sign in."

## Phase 4: User Story 2 — Download JSON (P2)

- [x] T008 [US2] Button "Download JSON" fetches the report with `getCrashTest(id)` and downloads it as `nirikkha-report-<id>.json`, pretty-printed with 2-space indentation
- [x] T009 [US2] Show a loading state on the button while fetching and an error text if the request fails; never crash the page

## Phase 5: Polish

- [x] T010 [P] Keyboard accessible buttons with visible focus rings; hidden when printing (`print:hidden` on the action row)
- [x] T011 [P] Reuse the Legal memo button style so the row looks consistent
- [x] T012 `npm run build` in `frontend` passes
- [x] T013 Manual check from `quickstart.md`: copy link on a featured report, open it signed out; download JSON and open it

## Dependencies

T001–T004 before T005–T009. US1 and US2 are independent. T012–T013 last.
