"""Click-based CLI for LIOS."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def cli() -> None:
    """LIOS – Legal Intelligence Operating System for EU sustainability compliance."""


@cli.command("query")
@click.argument("query_text")
@click.option("--employees", type=int, default=None, help="Number of employees")
@click.option("--turnover", type=float, default=None, help="Annual turnover in EUR")
@click.option("--listed/--not-listed", default=False, help="Is the company listed?")
@click.option("--jurisdiction", default=None, help="Jurisdiction (e.g. Germany)")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON")
def query_cmd(
    query_text: str,
    employees: int | None,
    turnover: float | None,
    listed: bool,
    jurisdiction: str | None,
    json_output: bool,
) -> None:
    """Run a legal query against the LIOS engine."""
    from lios.orchestration.engine import OrchestrationEngine

    engine = OrchestrationEngine()
    company_profile: dict = {}
    if employees is not None:
        company_profile["employees"] = employees
    if turnover is not None:
        company_profile["turnover_eur"] = turnover
    if listed:
        company_profile["listed"] = True
    if jurisdiction:
        company_profile["jurisdiction"] = jurisdiction

    jurisdictions = [jurisdiction] if jurisdiction else None

    result = engine.route_query(
        query=query_text,
        company_profile=company_profile or None,
        jurisdictions=jurisdictions,
    )

    if json_output:
        agent_count = len(result.consensus_result.agent_responses)
        click.echo(
            json.dumps(
                {
                    "query": result.query,
                    "intent": result.intent,
                    "answer": result.answer,
                    "consensus_reached": result.consensus_result.consensus_reached,
                    "confidence": result.consensus_result.confidence,
                    "agent_count": agent_count,
                },
                indent=2,
            )
        )
        return

    # Rich output
    agent_count = len(result.consensus_result.agent_responses)
    consensus_label = (
        f"Single-agent mode ({result.consensus_result.agreeing_agents[0]})"
        if agent_count == 1 and result.consensus_result.agreeing_agents
        else ("✅ Consensus reached" if result.consensus_result.consensus_reached else "⚠️  No consensus")
    )
    console.print(Panel(result.answer, title=f"[bold cyan]LIOS Answer[/] – {consensus_label}"))

    if result.decay_scores:
        table = Table(title="Regulatory Freshness Scores")
        table.add_column("Regulation")
        table.add_column("Score")
        table.add_column("Label")
        table.add_column("Last Updated")
        for d in result.decay_scores:
            color = "green" if d.score >= 80 else ("yellow" if d.score >= 60 else "red")
            table.add_row(
                d.regulation,
                f"[{color}]{d.score}[/{color}]",
                d.freshness_label,
                d.last_updated,
            )
        console.print(table)

    if result.conflicts:
        console.print(f"\n[yellow]⚠️  {len(result.conflicts)} jurisdiction conflict(s) detected.[/yellow]")
        for c in result.conflicts[:3]:
            console.print(
                f"  • [{c.severity.upper()}] {c.eu_regulation} vs {c.national_law} "
                f"({c.jurisdiction}): {c.conflict_type}"
            )


@cli.command("check-applicability")
@click.option("--regulation", required=True, help="Regulation name (CSRD, ESRS, EU_TAXONOMY, SFDR)")
@click.option("--employees", type=int, default=0, help="Number of employees")
@click.option("--turnover", type=float, default=0.0, help="Annual turnover in EUR")
@click.option("--balance-sheet", type=float, default=0.0, help="Balance sheet total in EUR")
@click.option("--listed/--not-listed", default=False)
@click.option("--sector", default="general", help="Business sector")
def check_applicability(
    regulation: str,
    employees: int,
    turnover: float,
    balance_sheet: float,
    listed: bool,
    sector: str,
) -> None:
    """Check if a regulation applies to your company."""
    from lios.features.applicability_checker import ApplicabilityChecker

    checker = ApplicabilityChecker()
    profile = {
        "employees": employees,
        "turnover_eur": turnover,
        "balance_sheet_eur": balance_sheet,
        "listed": listed,
        "sector": sector,
    }
    result = checker.check_applicability(regulation, profile)

    status = "✅ APPLICABLE" if result.applicable else "❌ NOT APPLICABLE"
    color = "green" if result.applicable else "red"
    console.print(Panel(
        f"[{color}]{status}[/{color}]\n\n{result.reason}",
        title=f"Applicability: {regulation.upper()}",
    ))
    if result.articles_cited:
        console.print(f"Articles cited: {', '.join(result.articles_cited)}")


@cli.command("roadmap")
@click.option("--employees", type=int, default=0)
@click.option("--turnover", type=float, default=0.0, help="Turnover in EUR")
@click.option("--balance-sheet", type=float, default=0.0)
@click.option("--listed/--not-listed", default=False)
@click.option("--sector", default="general")
@click.option("--jurisdiction", default="EU")
def roadmap(
    employees: int,
    turnover: float,
    balance_sheet: float,
    listed: bool,
    sector: str,
    jurisdiction: str,
) -> None:
    """Generate a compliance roadmap for your company."""
    from lios.features.compliance_roadmap import ComplianceRoadmapGenerator

    gen = ComplianceRoadmapGenerator()
    profile = {
        "employees": employees,
        "turnover_eur": turnover,
        "balance_sheet_eur": balance_sheet,
        "listed": listed,
        "sector": sector,
        "jurisdiction": jurisdiction,
    }
    rm = gen.generate_roadmap(profile)

    console.print(Panel(rm.summary, title="[bold]Compliance Roadmap[/bold]"))
    if rm.applicable_regulations:
        console.print(f"Applicable regulations: {', '.join(rm.applicable_regulations)}\n")

    for step in rm.steps:
        color = {"critical": "red", "high": "yellow", "medium": "blue", "low": "white"}.get(
            step.priority, "white"
        )
        console.print(
            f"  [{color}]{step.step_number}. [{step.priority.upper()}] {step.title}[/{color}]"
        )
        console.print(f"     Deadline: {step.deadline}")
        console.print(f"     Regulation: {step.regulation}")
        console.print()


@cli.command("regulations")
def regulations_cmd() -> None:
    """List all regulations in the LIOS knowledge base."""
    from lios.knowledge.regulatory_db import RegulatoryDatabase

    db = RegulatoryDatabase()
    regs = db.get_all_regulations()

    table = Table(title="LIOS Regulatory Knowledge Base")
    table.add_column("Key")
    table.add_column("Full Name")
    table.add_column("Effective Date")
    table.add_column("Last Updated")
    table.add_column("Articles")

    for r in regs:
        table.add_row(
            r["key"],
            r["full_name"],
            r["effective_date"],
            r["last_updated"],
            str(r["article_count"]),
        )
    console.print(table)


@cli.command("serve")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", type=int, default=8000, help="Port to listen on")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the LIOS FastAPI server."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn is not installed. Run: pip install uvicorn[/red]")
        sys.exit(1)

    console.print(f"[green]Starting LIOS server on {host}:{port}[/green]")
    uvicorn.run("lios.main:app", host=host, port=port, reload=reload)
