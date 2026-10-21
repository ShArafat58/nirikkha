# Quickstart & Validation Guide: Report Sharing and Export

**Feature**: `001-report-share-export`
**Phase**: Phase 1

## Prerequisites
- Node.js 18+ and npm installed.
- Frontend dependencies installed in `frontend/`.

## Manual Validation Steps

### Scenario 1: Copy Share Link on Featured Report
1. Open any featured report in the browser (e.g. `http://localhost:3000/report/demo-aapl` or live report ID).
2. Locate the action row next to the "Legal memo" button.
3. Click "Share link" (or "কপি লিঙ্ক").
4. **Expected Outcome**:
   - The report URL is in your clipboard.
   - A confirmation badge/toast appears saying "Link copied to clipboard!" and noting: "Featured reports are public and can be viewed without logging in."
   - The message automatically fades out after ~3.5 seconds.

### Scenario 2: Copy Share Link on Non-Featured / Custom Report
1. Open a non-featured report.
2. Click "Share link".
3. **Expected Outcome**:
   - Confirmation badge/toast displays explaining: "Recipients will need to sign in to Nirikkha to view this report."

### Scenario 3: Download JSON Export
1. Click "Download JSON" (or "JSON ডাউনলোড").
2. **Expected Outcome**:
   - Browser immediately triggers download of `nirikkha-report-<id>.json`.
   - Open the downloaded JSON in an editor: verify it is well-formed, indented with 2 spaces, and contains all report fields (health, factors, company, cik, decision).

### Scenario 4: Keyboard Navigation & Accessibility
1. Focus the actions using the Tab key.
2. Activate using Enter or Space.
3. **Expected Outcome**:
   - Visible outline focus ring is present.
   - Screen readers announce the action and the polite status update upon completion.

### Scenario 5: Print Preview
1. Press `Ctrl + P` (or `Cmd + P`).
2. **Expected Outcome**:
   - The action row with "Legal memo", "Share link", and "Download JSON" is hidden from the print layout.

### Scenario 6: Dual Language Toggle (EN/BN)
1. Toggle language to Bengali via the header language switch.
2. **Expected Outcome**:
   - Action buttons display Bengali labels ("শেয়ার লিঙ্ক", "JSON ডাউনলোড").
   - Confirmation messages display Bengali text without English fallback.

## Automated Verification
Run Next.js production build:
```powershell
cd frontend
npm run build
```
Ensure build completes with 0 errors and 0 type warnings.
