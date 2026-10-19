# DESIGN - Nirikkha

Direction: **Evidence Room** - an investigator's desk: dark room, evidence paper, highlighter marks, exact citations.
Plus a light "Paper" mode for reading long reports.

## Logo
- Full logo: `frontend/public/brand/logo.svg`
- Icon / favicon: `frontend/src/app/icon.svg`
- Concept: magnifying lens with a check mark over a highlighted line of a document = "find the evidence, verify it".
- TODO: convert text to outlines in Figma so the wordmark renders identically everywhere.

## Color tokens
| Token | Dark (default) | Light "Paper" | Use |
|---|---|---|---|
| bg | #0B1220 | #F5F1E8 | Page background |
| surface | #111A2E | #FFFFFF | Cards, panels |
| surface-2 | #18233B | #EFE9DB | Nested panels, table rows |
| border | #24304A | #E2DCCB | Dividers |
| text | #F5F1E8 | #1A2233 | Main text |
| muted | #8B95A7 | #5B6475 | Secondary text |
| accent | #F2B33D | #B7791F | Brand, evidence highlight, primary buttons |
| highlight | rgba(242,179,61,0.35) | rgba(242,179,61,0.45) | Background behind a cited passage |

## Semantic colors (always paired with a text label and icon, never color alone)
| Meaning | Color |
|---|---|
| Severity: critical | #E5484D |
| Severity: high | #F76B15 |
| Severity: medium | #FFC53D |
| Severity: low | #30A46C |
| Confidence: high | #30A46C |
| Confidence: medium | #4C9AFF |
| Confidence: low | #8B95A7 |
| Confidence: insufficient | #8B95A7 with diagonal stripes |
| Rule: PASS | #30A46C |
| Rule: POTENTIAL_GAP | #FFC53D |
| Rule: FAIL | #E5484D |
| Rule: INSUFFICIENT_EVIDENCE | #8B95A7 with diagonal stripes |

Rules:
- Severity and confidence are always two separate badges.
- INSUFFICIENT_EVIDENCE is never shown in green and never merged into "low risk".

## Typography (Google Fonts, all SIL Open Font License)
| Role | Font |
|---|---|
| UI and headings | IBM Plex Sans (400, 500, 600, 700) |
| Citations, page/section refs, numbers | IBM Plex Mono (400, 500) |
| Bengali | Noto Sans Bengali (400, 500, 700) |

## Images
- Only images with free commercial licences (e.g. Unsplash, Pexels), low opacity, compressed.