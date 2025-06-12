"""
Command-line interface for the GDPR Article-5 policy engine.

Examples
--------
# Permit
gdprctl eval tests/fixtures/sample_policy.json \
       use urn:data:customers \
       --purpose service-improvement \
       --role data-analyst \
       --location NL
"""

from __future__ import annotations

import typer
from gdpr_engine.evaluator import Decision, RequestCtx, evaluate
from gdpr_engine.loader import load_policy

# ---------------------------------------------------------------------------#
# Typer app                                                                   #
# ---------------------------------------------------------------------------#

app = typer.Typer(
    add_completion=False,
    help="GDPR Article-5 policy evaluator (prints Permit or Deny).",
)


# ---------------------------------------------------------------------------#
# eval sub-command                                                            #
# ---------------------------------------------------------------------------#


@app.command()
def eval(                                       # gdprctl **eval** …
    policy_file: str = typer.Argument(
        ...,
        exists=True,
        help="Path to a JSON/JSON-LD policy file",
    ),
    action: str = typer.Argument(
        ...,
        help="Requested action (e.g. 'use', 'distribute')",
    ),
    target: str = typer.Argument(
        ...,
        help="Target asset UID (e.g. 'urn:data:customers')",
    ),
    purpose: str | None = typer.Option(
        None,
        "--purpose",
        "-p",
        help="Business purpose of the processing request",
    ),
    role: str | None = typer.Option(
        None,
        "--role",
        "-r",
        help="Caller role (for role constraints)",
    ),
    location: str | None = typer.Option(
        None,
        "--location",
        "-l",
        help="ISO-3166 country code of caller / processing location",
    ),
) -> None:
    """Evaluate one request and exit 0 for Permit, 1 for Deny."""
    policy = load_policy(policy_file)

    ctx = RequestCtx(
        action=action,
        target=target,
        purpose=purpose,
        role=role,
        location=location,
    )
    decision: Decision = evaluate(policy, ctx)

    typer.echo(decision.value)
    if decision is not Decision.PERMIT:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------#
# `python -m gdpr_engine.cli …` entry-point                                   #
# ---------------------------------------------------------------------------#

def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # called via `python cli.py`
    app()
