You are drafting an internal legal-risk memo about {company} for a team deciding: {decision}
Use ONLY the FINDINGS and RULES provided. They come from a governance crash-test of public SEC filings.

Write 3 to 5 NON-OBVIOUS risks. Each risk must:
1. Connect at least TWO findings, cited by id (for example ["REL-2", "CON-3"]), whose combination raises a question
   that neither finding raises alone.
2. Cite at least one rule copied EXACTLY from the RULES list (for example "Reg S-K Item 404(a)").
3. Explain in one sentence why it is non-obvious (why_non_obvious).
4. Give one concrete recommended_action for legal or compliance.

Strict rules:
- Do not invent facts, names, numbers, rules, statutes or cases. Do not use outside knowledge.
- Neutral language: "may", "potential", "question to review". Never state misconduct or a violation.
- Never use words that imply intent, such as conceal, hide, hidden, mislead, deceive, fraud, cover-up, manipulate.
- The findings come from excerpts. Never write that the filings "do not provide", "lack" or "do not show" something.
  Write that it "was not found in the reviewed passages".
- The RULES are SEC Regulation S-K DISCLOSURE requirements. Describe each rule only by the meaning given in the
  RULES list. Never write that a rule requires, mandates or obligates conduct; write that it requires disclosure.
- Read each finding's reviewer notes. If a finding is marked needs_review, say the conclusion depends on that review.
- severity is how serious the risk would be for the decision IF confirmed: low, medium, high or critical.
- executive_summary under 100 words; each analysis under 120 words.

Return only a JSON object:
{"executive_summary": "...", "risks": [{"title": "...", "finding_ids": ["REL-2", "CON-3"], "rules": ["Reg S-K Item 407(h)"], "severity": "high", "analysis": "...", "why_non_obvious": "...", "recommended_action": "..."}]}