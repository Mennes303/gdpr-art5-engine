# GDPR Article-5 Engine

**Python micro-service that enforces core GDPR Article 5 principles—purpose limitation, storage limitation, spatial integrity & confidentiality, and accountability—at request time.**  
Originally built for the author’s 2025 bachelor thesis on compliance inside *Zero-Person Companies* (fully autonomous multi-agent businesses).

---

## Feature overview

| Category | Details |
|----------|---------|
| **Policy-decision point** | Pure-Python `evaluate(policy, ctx) → Decision` returning **Permit / Deny** plus optional retention duties. |
| **Declarative policy model** | Compact JSON (ODRL-inspired) covering roles, purposes, data targets, locations, and retention periods. |
| **FastAPI service** | `POST /decision`, full CRUD under `/policies`, audit at `/audit`, duty helpers under `/duties/*`. |
| **Hash-chained audit trail** | Append-only JSONL file—each line has a SHA-256 digest and is chained to the previous one. |
| **Retention duties** | Duties stored in SQLite; hourly scheduler (or `POST /duties/flush`) executes overdue deletions and logs a **Delete** entry. |
| **100 % corpus test** | 58-row CSV corpus exercised by pytest for exact Permit/Deny matching (0 false positives/negatives). |
| **Load-testing assets** | Async bench script (`scripts/bench_async.py`) or Locust workload (`locustfile.py`) with *burst*, *steady*, *dutyflush* tags. |
| **CLI** | `gdprctl` shell command: `gdprctl <policy.json> use urn:data:customers -p service-improvement`. |

---

## Quick start

```bash
# 1 · Clone & enter
git clone https://github.com/Mennes303/gdpr-art5-engine.git
cd gdpr-art5-engine

# 2 · Create & activate a virtual-env
python -m venv .venv
source .venv/bin/activate      # PowerShell: .\.venv\Scripts\Activate.ps1

# 3 · Install runtime + dev extras (PEP-621 metadata)
pip install -e .[dev]          # fastapi, uvicorn, pydantic, pytest, ruff, locust …

# 4 · Launch the API (auto-reload on code changes)
uvicorn gdpr_engine.api:app --reload
