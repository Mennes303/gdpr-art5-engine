"""
CLI integration test: ensure ``gdprctl`` exits with status 0 and prints
``Permit`` when the request satisfies the sample policy.
"""

import subprocess
import sys

POLICY = "tests/fixtures/sample_policy.json"


def test_cli_permit():
    """Expect `Permit` and exit code 0 for a matching request."""
    cmd = [
        sys.executable,
        "-m",
        "gdpr_engine.cli",
        POLICY,  # path to policy file (top‑level positional argument)
        "use",
        "urn:data:customers",
        "--purpose",
        "service-improvement",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "Permit"
