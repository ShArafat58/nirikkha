# Local models and Private mode

Private mode runs every AI step of a Crash-Test on models that live on the same computer.
No document text, passage or prompt is sent to a cloud provider.

## Hardware used for the numbers below

| Item    | Value                                                        |
| ------- | ------------------------------------------------------------ |
| Machine | Windows laptop                                               |
| RAM     | 8 GB                                                         |
| GPU     | None (Intel integrated graphics); everything runs on the CPU |

## Local runtimes and models

| Runtime                      | Model                    | Size    | Used for                                                                  |
| ---------------------------- | ------------------------ | ------- | ------------------------------------------------------------------------- |
| Ollama                       | `qwen2.5:1.5b`           | 986 MB  | JSON outputs, classification, rule and Sentinel checks in private mode    |
| Ollama                       | `gemma3:1b`              | 806 MB  | Short summaries and prose in private mode                                 |
| ONNX Runtime (via fastembed) | `BAAI/bge-small-en-v1.5` | ~130 MB | Embeddings (384 dimensions) for retrieval, always local in every mode     |
| ONNX Runtime (via fastembed) | `ms-marco-MiniLM-L-6-v2` | ~90 MB  | Cross-encoder reranking of retrieved passages, always local in every mode |

Embeddings and reranking were already local before Private mode. Private mode moves the remaining LLM steps to Ollama.

## Measured speed (21 Oct 2026, CPU only)

| Model          | Load  | Prompt reading | Generation    |
| -------------- | ----- | -------------- | ------------- |
| `gemma3:1b`    | 2.9 s | 79.6 tokens/s  | 17.4 tokens/s |
| `qwen2.5:1.5b` | 3.5 s | 106.1 tokens/s | 16.0 tokens/s |

### A full private Crash-Test

Apple Inc. (CIK 320193), decision: "Before we proceed with this supplier partnership, identify governance risks and evidence gaps."
Report `57d5a562-637b-4ea2-934f-e7dc3c55aaf2`.

| Stage                            | Time                |
| -------------------------------- | ------------------- |
| Safety check                     | 13.8 s              |
| Load filings, graph and rules    | 75.8 s              |
| Turn the decision into questions | 16.7 s              |
| Find evidence passages           | 30.2 s              |
| Answer from the evidence only    | 53.7 s              |
| Reliability Sentinel             | 15.3 s              |
| **Total**                        | **about 7 minutes** |

Check after the run: the report metadata lists only `provider: ollama` with `qwen2.5:1.5b` and `gemma3:1b`.
No Groq, Gemini or OpenAI entry appears.

## How Private mode stays private

- **Fail closed.** When a Crash-Test is private, the LLM router only calls the local Ollama URL. If Ollama is not running or times out, the run stops with `PrivateModeUnavailable`. It never falls back to a cloud model.
- **Checked before queuing.** `POST /api/crash-tests` with `private: true` returns `409` when `GET /api/private/status` reports the runtime is unavailable.
- **Visible.** The progress view and the report show a "Private mode · local models" badge with the model names.
- **Cost.** Local calls are logged with cost `0.0`.
- Tests: `backend/tests/test_private_mode.py` (cloud clients are never called in private mode, including when Ollama is down).

On the public deployment the runtime is absent, so the switch is shown but disabled with the note that Private mode is available when Nirikkha runs on your own machine or in an Enterprise install.

## Quality trade-off (honest note)

Small local models are less critical than the large cloud models. On the same Apple decision the cloud run scored
Health 87, the private run scored Health 94 with 8 findings and 5 "Insufficient Evidence" items.
Private mode gives confidentiality, not equal depth. For important decisions use a larger local model on stronger
hardware, or keep human review on every flagged item. Rules, evidence citations and "Insufficient Evidence" handling
are the same in both modes because they come from the rule engine and the retrieval layer, not from the model.

## Run it yourself

```powershell
winget install --id Ollama.Ollama -e
ollama pull qwen2.5:1.5b
ollama pull gemma3:1b
cd backend
uvicorn app.main:app --port 8000          # terminal 1
python -m app.api.worker                  # terminal 2
cd ..\frontend
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev                               # terminal 3
```

Open http://localhost:3000, go to Crash-Test, switch on **Private mode**, and run.
`GET http://localhost:8000/api/private/status` should return `available: true` with both model names.
