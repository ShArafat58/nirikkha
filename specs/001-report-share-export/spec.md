# Feature Specification: Report Sharing and Export

**Feature Branch**: `001-report-share-export`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Report sharing and export. On the Crash-Test report page (frontend/src/app/report/[id]/page.tsx), add two actions next to the Legal memo button: (a) Copy share link: copies the report URL to the clipboard and shows a short confirmation; it explains that featured reports are public and other reports need the viewer to sign in. (b) Download JSON: downloads the report data the page already has as nirikkha-report-<id>.json, pretty-printed, so analysts can archive or audit it. Both actions EN/BN via the existing i18n, keyboard accessible, hidden when printing. No backend changes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Copy Shareable Report Link (Priority: P1)

As a governance analyst or compliance officer reviewing a crash-test report, I want to quickly copy the direct URL of the report to my clipboard along with clear visibility of access permissions (public vs sign-in required), so that I can share it with colleagues or stakeholders.

**Why this priority**: Fast, clear sharing is vital for governance collaboration; users must understand access rules (featured demo reports are publicly accessible, custom company reports require viewer authentication) without guesswork.

**Independent Test**: Navigate to any completed report page, trigger the "Copy share link" action. Confirm that the URL is placed onto the clipboard, a confirmation message appears explaining the access boundary (public vs sign-in required based on report type), and the message automatically disappears after a short delay.

**Acceptance Scenarios**:

1. **Given** a user is viewing a featured (public demo) report, **When** they click or activate via keyboard the "Copy share link" action, **Then** the report URL is copied to the clipboard, and a confirmation notice displays informing them that this featured report is publicly viewable.
2. **Given** a user is viewing a custom/non-featured report, **When** they trigger the "Copy share link" action, **Then** the report URL is copied to the clipboard, and a confirmation notice displays explaining that recipients will need to sign in to view the analysis.
3. **Given** the share link confirmation is currently visible, **When** several seconds elapse, **Then** the confirmation notice gracefully dismisses.

---

### User Story 2 - Download Complete Report as JSON (Priority: P2)

As a risk auditor or technical analyst, I want to download the entire structured report data as a formatted JSON file named `nirikkha-report-<id>.json`, so that I can archive the evidence-backed findings, feed them into local audit pipelines, or inspect raw machine-readable disclosures offline.

**Why this priority**: Compliance records and audit trails require portable, machine-readable snapshots of evidence findings and scores as of the analysis timestamp.

**Independent Test**: Navigate to a completed report page, trigger "Download JSON". Confirm that a file named `nirikkha-report-<id>.json` is immediately downloaded, containing the complete, valid, indented JSON payload matching the active report state.

**Acceptance Scenarios**:

1. **Given** an analyst is viewing a completed crash test report with identifier `test-123`, **When** they activate "Download JSON", **Then** the browser downloads a file named `nirikkha-report-test-123.json` containing the complete report data indented with standard formatting.
2. **Given** the report is still loading or in an error state, **When** the page renders, **Then** the export action is disabled or withheld until report data is fully available.

---

### User Story 3 - Clean Print and Multilingual Presentation (Priority: P3)

As a user printing or saving the report as a PDF for a board packet, or viewing in Bengali (BN), I want the action buttons hidden during print and properly localized in both English and Bengali, so that reports remain publication-ready and accessible.

**Why this priority**: Nirikkha constitutional rules mandate strict dual-language accessibility (EN/BN) and clean, professional presentation without interactive UI clutter in printed memos.

**Independent Test**: Switch language between English and Bengali; verify all action labels and confirmation toasts display in the active language. Trigger print preview and verify sharing/export buttons are hidden.

**Acceptance Scenarios**:

1. **Given** language is set to Bengali, **When** viewing the report page actions, **Then** the action buttons, tooltips, and confirmation notices display accurate Bengali text.
2. **Given** the user triggers browser print (or PDF export), **When** print styles are applied, **Then** the sharing and export action controls are omitted (`print:hidden`).
3. **Given** a keyboard-only user navigating the header actions, **When** pressing Tab and Enter/Space, **Then** focus indicators are clearly visible and both actions can be triggered without a mouse.

---

### Edge Cases

- **Clipboard API unavailable or permission denied**: If the browser denies clipboard permissions (e.g., non-secure context or user rejection), the application gracefully falls back or informs the user without throwing unhandled exceptions.
- **Very large report payloads**: JSON serialization and download blob creation must execute without freezing the browser UI.
- **Report with special characters in ID**: Filename construction must cleanly sanitize or interpolate the report ID.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a "Copy share link" button positioned adjacent to the Legal Memo action on the Crash-Test report page.
- **FR-002**: System MUST copy the absolute canonical report URL to the user's system clipboard upon activation of "Copy share link".
- **FR-003**: System MUST display an immediate confirmation notice upon copying, explaining access permission rules:
  - If the report is a featured public demo (`featured: true`), indicate that the link is publicly accessible without login.
  - If the report is an authenticated/non-featured test, indicate that recipients must sign in to view it.
- **FR-004**: System MUST automatically dismiss the share confirmation notice after 3 to 4 seconds.
- **FR-005**: System MUST provide a "Download JSON" button adjacent to the share and legal memo actions.
- **FR-006**: System MUST generate and trigger client-side download of `nirikkha-report-<id>.json` containing the complete report data in pretty-printed JSON formatting (2 spaces indentation).
- **FR-007**: System MUST localize all button labels, aria attributes, and confirmation notices in both English (EN) and Bengali (BN) using the application's central i18n system.
- **FR-008**: System MUST hide all share and export action controls when printing or exporting to PDF via CSS print media styles (`print:hidden`).
- **FR-009**: System MUST ensure both action buttons are fully keyboard-navigable with accessible focus rings and semantic HTML button elements.
- **FR-010**: System MUST execute all actions purely on the client side using the report data already present on the page, requiring no new backend endpoints or modifications.

### Key Entities *(include if feature involves data)*

- **CrashTestReport**: The active governance assessment object containing report ID, company name, CIK, health score, band, four investigation findings, citations, and featured flag.
- **ReportShareNotice**: Transient confirmation state conveying clipboard copy success and audience access policy (public vs login required).
- **ReportExportArtifact**: The downloaded file named `nirikkha-report-<id>.json` representing the standalone audit snapshot.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can copy the share link with access context in a single click (under 1 second).
- **SC-002**: 100% of downloaded JSON files validate as well-formed, pretty-printed JSON matching the exact in-memory report schema.
- **SC-003**: Zero interactive sharing/export controls appear in printed output or PDF exports.
- **SC-004**: 100% of user-facing strings in the feature are translated into both English and Bengali without English fallbacks in Bengali mode.
- **SC-005**: All actions are accessible and operable using keyboard navigation alone (Tab + Enter / Space).

## Assumptions

- The report page already fetches and holds the complete `Report` object in client state.
- The browser environment supports standard Web APIs: `navigator.clipboard.writeText`, `Blob`, and `URL.createObjectURL`.
- Featured reports can be identified by the `featured` boolean or source flag on the report data object.
- No modifications to the backend FastAPI service or database schema are needed.
