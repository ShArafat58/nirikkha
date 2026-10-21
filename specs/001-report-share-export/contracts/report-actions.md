# UI & Action Contracts: Report Sharing and Export

**Feature**: `001-report-share-export`
**Phase**: Phase 1

## Component Contracts

### Component: `ReportActions`

Located at: `frontend/src/components/report/report-actions.tsx` (or integrated in report header).

#### Props Contract

```typescript
export interface ReportActionsProps {
  id: string;
  report: Report;
  source?: string;
  featured?: boolean;
}
```

#### User Interaction Behaviors

1. **Copy Share Link**:
   - Computes canonical URL: `window.location.origin + "/report/" + id`.
   - Copies to clipboard using `navigator.clipboard.writeText`.
   - Sets `copied: true` and reveals notice card:
     - Public notice if `source === "featured" || source === "demo" || featured === true || report.featured === true`.
     - Sign-in notice otherwise.
   - Clears `copied` after 3500ms timeout.
   - Includes accessible aria-label and live region announcement (`aria-live="polite"`).

2. **Download JSON**:
   - Triggers download of `nirikkha-report-${id}.json`.
   - File contains `JSON.stringify(report, null, 2)`.
   - Revokes object URL immediately after click.

3. **Print Media Behavior**:
   - Entire action group possesses `print:hidden` CSS utility class so it does not render during paper print or PDF export.

4. **Localization Contract**:
   - Reads active language and dictionary from `useApp()`.
   - Uses `t("rep.share")`, `t("rep.shareCopied")`, `t("rep.sharePublicNote")`, `t("rep.shareAuthNote")`, `t("rep.downloadJson")`.
