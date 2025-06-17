import subprocess
import sys
POLICY = "tests/fixtures/sample_policy.json"


def test_cli_permit():
    """
    gdprctl should exit 0 and print 'Permit'
    when the request matches the policy constraints.
    """
    cmd = [
        sys.executable,
        "-m",
        "gdpr_engine.cli",
        POLICY,                       # ← no "eval" sub-command
        "use",
        "urn:data:customers",
        "--purpose",
        "service-improvement",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "Permit"
