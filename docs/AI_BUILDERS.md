# Frontend AI builders

Five AI UI builders each produced one real part of the Nirikkha frontend. Every output was reviewed,
adapted to the site's theme tokens and EN/BN text, and built with `npm run build` before merging.

| Builder          | What it built                                           | Where it lives                                                               | Link                                                              | Changes on review                                                                                                  |
| ---------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| v0 (Vercel)      | 404 page with magnifying-glass illustration             | `frontend/src/app/not-found.tsx`                                             | https://v0.app/sharafat58s-projects/chat/ufJXysDLYiq              | Colour classes mapped to our tokens (`bg-bg`, `text-text`, `text-accent-contrast`); EN/BN text                     |
| Bolt.new         | Empty state for "My reports" with a three-step guide    | `frontend/src/components/reports-empty-state.tsx`                            | https://bolt.new/p/72252449                                       | **Bug fixed:** steps array was spread into an object, which would break `.map`; missing animation utility replaced |
| Lovable          | Site footer with product links and responsible-use note | `frontend/src/components/site-footer.tsx` (+ `site-footer-i18n.tsx`)         | https://lovable.dev/projects/ed9baf51-2e9f-4aeb-9ac6-9d7558b663fc | Used as generated; Bengali wrapper; hidden when printing memos                                                     |
| Claude Artifacts | Pricing FAQ accordion (native `details`/`summary`)      | `frontend/src/components/pricing-faq.tsx` (+ `pricing-faq-i18n.tsx`)         | https://claude.ai/artifact/JYA7TcanCocrbDogeWNL28                 | Used as generated; Bengali items                                                                                   |
| Gemini Canvas    | "How to read a report" glossary of result types         | `frontend/src/components/result-glossary.tsx` (+ `result-glossary-i18n.tsx`) | https://share.gemini.google/OhgvfuAyzWSh                          | Hard-coded English subtitle turned into a prop for Bengali                                                         |

## How we used them

Each builder got the same constraints: one component, TypeScript and Tailwind only, no external UI or icon libraries,
only our theme colour classes, accessible markup, and props for every visible string so we could pass Bengali.
We then read the code line by line before merging. AI builders were fast for layout and illustration, but one of the
five outputs (Bolt.new) contained a runtime bug that the type checker did not catch, which is why nothing is merged unreviewed.

The core product (report, graph, Replay, Radar, admin) was written in the IDE; these builders were used for supporting UI.
