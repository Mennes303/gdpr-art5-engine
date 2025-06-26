"""
Command‑line interface (CLI) for the GDPR Article‑5 policy engine.

Example – permit request
------------------------
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

# Typer application instance
app = typer.Typer(
    add_completion=False,
    help="GDPR Article‑5 policy evaluator (prints Permit or Deny).",
)


@app.command()
def eval(  # noqa: D401 – CLI verb, not a docstring
    policy_file: str = typer.Argument(
        ..., exists=True, help="Path to a JSON or JSON‑LD policy file"
    ),
    action: str = typer.Argument(..., help="Requested action, e.g. 'use'"),
    target: str = typer.Argument(..., help="Target asset UID"),
    purpose: str | None = typer.Option(
        None, "--purpose", "-p", help="Business purpose of the request"
    ),
    role: str | None = typer.Option(
        None, "--role", "-r", help="Caller role for role constraints"
    ),
    location: str | None = typer.Option(
        None, "--location", "-l", help="ISO‑3166 country code of caller"
    ),
) -> None:
    """Evaluate one request and exit with *0* for Permit, *1* for Deny."""

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


# ``python -m gdpr_engine.cli`` entry‑point

def main() -> None:  # pragma: no cover
    """Entry‑point for ``python -m gdpr_engine.cli``."""
    app()


if __name__ == "__main__":  # called via ``python cli.py``
    app()
