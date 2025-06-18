# GDPR-Art-5 Engine

**Python micro-service that enforces four GDPR Article 5 principles—purpose limitation, data minimisation, storage limitation, and accountability—at request time for AI agents or any HTTP client.**  
The project was developed as part of the author’s 2025 bachelor-thesis on compliance in Zero-Person Companies (ZPC).

---

## Features
| Category | Details |
| -------- | ------- |
| **Policy-decision point (PDP)** | Pure-Python evaluator `evaluate(policy, ctx) → Decision` (permit / deny / obligations). |
| **Declarative policy** | YAML / JSON files describe roles, purposes, data targets, locations and retention periods. |
| **Audit trail** | Every decision is appended as a JSON line with timestamp, request context and duty changes. |
| **Storage-limitation duties** | Automatic retention timer creation / refresh; duties persisted in `duties.jsonl`. |
| **FastAPI service** | `POST /decision` wrapper so any agent or cURL client can obtain a decision over HTTP. |
| **Battery of tests** | Pytest corpus (58 scenarios) for 100 % correctness, plus audit-coverage checks. |
| **Performance script** | `scripts/bench_async.py` launches 100 concurrent clients and reports p50 / p95 / p99 latencies. |

---

## Quick start

```bash
# 1 · clone & enter
git clone https://github.com/Mennes303/gdpr-art5-engine.git
cd gdpr-art5-engine

# 2 · create & activate a virtual-env (PowerShell syntax shown)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3 · install Python dependencies
pip install -r requirements.txt        # httpx, fastapi, uvicorn, pyyaml, click, pytest…

# 4 · launch the REST API (4 worker processes on localhost:8000)
uvicorn gdpr_engine.api:app --host 127.0.0.1 --port 8000 --workers 4
