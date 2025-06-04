import json
from pathlib import Path
from gdpr_engine.model import Policy

def load_policy(path: str | Path) -> Policy:
    """Load a Policy from a JSON file (JSON-LD context ignored for now)."""
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    return Policy.model_validate(data)