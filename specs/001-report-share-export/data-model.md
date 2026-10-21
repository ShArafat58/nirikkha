# Data Model: Report Sharing and Export

**Feature**: `001-report-share-export`
**Phase**: Phase 1

## Entities & Interfaces

### 1. Report Share State
Represents transient component state while managing clipboard actions and feedback notifications.

| Field | Type | Description |
|---|---|---|
| `copied` | `boolean` | Indicates whether the share URL was recently copied to the clipboard. |
| `isFeatured` | `boolean` | Flag indicating whether this report is a publicly accessible featured demo. |
| `timerId` | `NodeJS.Timeout \| null` | Reference to auto-dismiss timer for the confirmation notice. |

### 2. Report Export Payload
Represents the serialized JSON file content exported by the client.

| Field | Type | Description |
|---|---|---|
| `company` | `string` | Target company name evaluated in the Crash-Test. |
| `cik` | `string` | SEC Central Index Key (10-digit zero-padded or numeric string). |
| `as_of` | `string` | Date snapshot cutoff (YYYY-MM-DD). |
| `decision` | `string` | Corporate decision or query evaluated against filings. |
| `health` | `Health` | Health score object containing numerical score, band, coverage metrics, and deductions. |
| `summary` | `object` | Findings count and Risk Sentinel verification results. |
| `retrieval_mode` | `string?` | Optional retrieval pipeline mode indicator. |
| `private` | `boolean?` | Flag indicating if test was run under private local mode. |
| `usage` | `object?` | Audit metrics for token consumption and latency. |
| `findings` | `array?` | Extracted investigation findings, passages, citations, and severities. |

### 3. File Download Specification
- **Filename convention**: `nirikkha-report-${encodeURIComponent(id)}.json`
- **MIME type**: `application/json;charset=utf-8`
- **Formatting**: Pretty-printed with 2-space indentation (`JSON.stringify(report, null, 2)`)
