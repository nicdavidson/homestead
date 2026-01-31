#!/usr/bin/env python3
"""
Hearth - Main Entry Point
Infrastructure for AI entity emergence
"""

import sys
import os
import logging
from pathlib import Path

# Add hearth directory to path so imports work correctly
HEARTH_DIR = Path(__file__).parent.resolve()
if str(HEARTH_DIR) not in sys.path:
    sys.path.insert(0, str(HEARTH_DIR))

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hearth")


def get_config(config_path=None):
    """Get configuration."""
    from core.config import Config
    return Config(config_path)


@click.group(invoke_without_command=True)
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file path')
@click.option('--mock', is_flag=True, help='Run in mock mode (no API calls)')
@click.pass_context
def cli(ctx, config, mock):
    """Hearth - Infrastructure for AI entity emergence."""
    ctx.ensure_object(dict)

    # Show help if no command given
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)

    try:
        cfg = get_config(config)
        if mock:
            cfg._data['mock_mode'] = True
        ctx.obj['config'] = cfg
    except FileNotFoundError:
        if ctx.invoked_subcommand != 'setup':
            console.print("[red]No configuration found. Run setup.sh first.[/red]")
            sys.exit(1)


@cli.command()
def setup():
    """Run interactive setup."""
    import subprocess
    setup_script = Path(__file__).parent / "setup.sh"
    if setup_script.exists():
        subprocess.run(["bash", str(setup_script)])
    else:
        console.print("[red]Setup script not found.[/red]")


@cli.command()
@click.option('--agent', type=click.Choice(['main', 'sonnet', 'grok', 'auto'], case_sensitive=False),
              default='main', help='Agent to use (default: main)')
@click.pass_context
def chat(ctx, agent):
    """Start interactive chat session."""
    config = ctx.obj['config']

    from integrations.cli import run_cli_chat
    run_cli_chat(config, agent=agent)


@cli.command()
@click.pass_context
def daemon(ctx):
    """Run the background daemon (nightshift)."""
    config = ctx.obj['config']
    
    from agents.nightshift import Nightshift
    
    console.print(Panel("🔥 Starting Hearth daemon...", style="bold"))
    
    nightshift = Nightshift(config)
    nightshift.run()


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind')
@click.option('--port', default=8420, help='Port to bind')
@click.pass_context
def serve(ctx, host, port):
    """Start unified service (Nightshift + REST API + Web UI)."""
    config = ctx.obj['config']

    from service import run_service

    console.print("[bold]🔥 Starting Hearth unified service...[/bold]")

    run_service(host=host, port=port, config=config)


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind')
@click.option('--port', default=8420, help='Port to bind')
@click.pass_context
def web(ctx, host, port):
    """Start the web interface only (no daemon)."""
    config = ctx.obj['config']

    from web.app import create_app
    import uvicorn

    console.print(f"[bold]Starting web UI at http://{host}:{port}[/bold]")

    app = create_app(config)
    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current status."""
    config = ctx.obj['config']
    
    from core.identity import Identity
    from core.costs import CostTracker
    from core.state import StateDB
    
    identity = Identity(config)
    costs = CostTracker(config)
    state = StateDB(str(config.entity_home / "data" / "hearth.db"))

    # Entity info
    name = identity.get_name()
    console.print(Panel(f"[bold]{name}[/bold]", title="Entity", style="cyan"))

    # Budget
    budget = costs.get_budget_status()
    budget_color = "green" if budget.percent_used < 80 else "yellow" if budget.percent_used < 95 else "red"
    console.print(Panel(
        f"Daily: ${budget.daily_spent:.2f} / ${budget.daily_budget:.2f} ({budget.percent_used:.0f}%)\n"
        f"Remaining: ${budget.daily_remaining:.2f}",
        title="Budget",
        style=budget_color
    ))

    # Tasks
    task_stats = state.get_task_stats()
    console.print(Panel(
        f"Pending: {task_stats['by_status'].get('pending', 0)}\n"
        f"Completed today: {task_stats['completed_today']}",
        title="Tasks"
    ))


@cli.command()
@click.pass_context
def costs(ctx):
    """Show detailed cost report."""
    config = ctx.obj['config']
    
    from core.costs import CostTracker
    
    tracker = CostTracker(config)
    report = tracker.format_report()
    
    console.print(Markdown(report))


@cli.command()
@click.pass_context
def reflect(ctx):
    """Trigger a reflection."""
    config = ctx.obj['config']
    
    from agents.sonnet import SonnetAgent
    
    console.print("[bold]Triggering reflection...[/bold]")
    
    agent = SonnetAgent(config)
    response = agent.reflect()
    
    console.print(Panel(response.content, title="Reflection"))
    console.print(f"[dim]Cost: ${response.cost:.4f}[/dim]")


@cli.command()
@click.pass_context
def synthesis(ctx):
    """Run weekly Opus synthesis (manual trigger)."""
    config = ctx.obj['config']

    from agents.opus import OpusAgent

    console.print("[yellow]This will use Opus via CLI (no cost with Pro subscription).[/yellow]")

    if not click.confirm("Proceed?"):
        return

    console.print("[bold]Running weekly synthesis...[/bold]")

    agent = OpusAgent(config)
    response = agent.weekly_synthesis()

    console.print(Panel(response.content, title="Weekly Synthesis"))
    console.print(f"[dim]Cost: ${response.cost:.4f} (CLI - no charge)[/dim]")


@cli.command()
@click.pass_context
def name(ctx):
    """Trigger the naming ceremony."""
    config = ctx.obj['config']

    from agents.opus import OpusAgent
    from core.identity import Identity

    identity = Identity(config)

    if identity.is_named():
        console.print(f"[yellow]Already named: {identity.get_name()}[/yellow]")
        if not click.confirm("Run naming ceremony anyway?"):
            return

    console.print("[bold]🔥 The Naming Ceremony[/bold]")
    console.print("[dim]The entity will propose names with reasoning.[/dim]\n")

    agent = OpusAgent(config)
    response = agent.naming_ceremony()

    console.print(Panel(response.content, title="Naming Ceremony"))
    console.print(f"\n[dim]Cost: ${response.cost:.4f}[/dim]")

    console.print("\n[bold]To set a name:[/bold]")
    console.print("  hearth setname <chosen_name>")


@cli.command()
@click.argument('new_name')
@click.pass_context
def setname(ctx, new_name):
    """Set the entity name explicitly."""
    config = ctx.obj['config']

    from core.identity import Identity

    identity = Identity(config)
    current = identity.get_name()

    if current != "_":
        console.print(f"[yellow]Current name: {current}[/yellow]")
        if not click.confirm(f"Change name to '{new_name}'?"):
            return

    identity.set_name(new_name)
    console.print(f"[green]✓[/green] Entity named: [bold]{new_name}[/bold]")
    console.print(f"[dim]Saved to state database and logged to reflections[/dim]")

    # Offer to apply name system-wide
    if config.entity_user == "_":
        console.print("\n[yellow]Would you like to apply this name to the system user and hostname?[/yellow]")
        console.print("[dim]This will rename user '_' to '{}'[/dim]".format(new_name.lower()))
        if click.confirm("Run 'hearth apply-name' now?"):
            ctx.invoke(apply_name)


@cli.command()
@click.option('--hostname/--no-hostname', default=True, help='Also update system hostname')
@click.pass_context
def apply_name(ctx, hostname):
    """Apply entity's chosen name to system user and hostname."""
    config = ctx.obj['config']

    from core.identity import Identity
    import subprocess

    identity = Identity(config)
    entity_name = identity.get_name()

    if entity_name == "_":
        console.print("[red]Entity has not chosen a name yet.[/red]")
        console.print("[dim]Use 'hearth name' to trigger naming ceremony[/dim]")
        return

    # Convert to lowercase username
    username = entity_name.lower()
    current_user = config.entity_user

    if current_user == username:
        console.print(f"[yellow]System already configured for '{username}'[/yellow]")
        return

    console.print(f"[bold]Applying entity name: {entity_name}[/bold]")
    console.print(f"[dim]System user: {current_user} → {username}[/dim]")

    if not click.confirm("This will stop the service, rename the user, and update system files. Continue?"):
        return

    try:
        # Stop service
        console.print("\n[yellow]Stopping Hearth service...[/yellow]")
        subprocess.run(["sudo", "systemctl", "stop", "hearth"], check=True)

        # Check if new username already exists
        result = subprocess.run(["id", username], capture_output=True)
        if result.returncode == 0:
            console.print(f"[red]User '{username}' already exists. Cannot proceed.[/red]")
            subprocess.run(["sudo", "systemctl", "start", "hearth"])
            return

        # Rename user
        console.print(f"[yellow]Renaming user '{current_user}' to '{username}'...[/yellow]")
        subprocess.run(["sudo", "usermod", "-l", username, current_user], check=True)

        # Rename group
        subprocess.run(["sudo", "groupmod", "-n", username, current_user], check=True)

        # Move home directory
        old_home = f"/home/{current_user}"
        new_home = f"/home/{username}"
        console.print(f"[yellow]Moving home directory: {old_home} → {new_home}...[/yellow]")
        subprocess.run(["sudo", "usermod", "-d", new_home, "-m", username], check=True)

        # Update comment
        subprocess.run(["sudo", "usermod", "-c", f"Hearth Entity ({entity_name})", username], check=True)

        # Update .env file
        console.print("[yellow]Updating .env configuration...[/yellow]")
        env_path = Path("/opt/hearth/.env")
        if env_path.exists():
            content = env_path.read_text()
            content = content.replace(f"ENTITY_HOME={old_home}", f"ENTITY_HOME={new_home}")
            content = content.replace(f"ENTITY_USER={current_user}", f"ENTITY_USER={username}")
            env_path.write_text(content)
            subprocess.run(["sudo", "chmod", "600", str(env_path)], check=True)

        # Update systemd service
        console.print("[yellow]Updating systemd service...[/yellow]")
        service_content = f"""[Unit]
Description=Hearth - AI Entity ({entity_name})
After=network.target

[Service]
Type=simple
User={username}
Group={username}
WorkingDirectory=/opt/hearth
Environment="PATH=/opt/hearth/venv/bin:/usr/bin:/bin"
EnvironmentFile=/opt/hearth/.env
ExecStart=/opt/hearth/venv/bin/python /opt/hearth/main.py serve
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        Path("/tmp/hearth.service").write_text(service_content)
        subprocess.run(["sudo", "cp", "/tmp/hearth.service", "/etc/systemd/system/hearth.service"], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)

        # Update hostname if requested
        if hostname:
            console.print(f"[yellow]Updating hostname to '{username}'...[/yellow]")
            subprocess.run(["sudo", "hostnamectl", "set-hostname", username], check=True)

        # Start service
        console.print("[yellow]Starting Hearth service...[/yellow]")
        subprocess.run(["sudo", "systemctl", "start", "hearth"], check=True)

        console.print(f"\n[green]✓[/green] [bold]System successfully configured for {entity_name}[/bold]")
        console.print(f"[dim]System user: {username}[/dim]")
        console.print(f"[dim]Home directory: {new_home}[/dim]")
        if hostname:
            console.print(f"[dim]Hostname: {username}[/dim]")
            console.print("\n[yellow]Reboot recommended for hostname to take full effect:[/yellow]")
            console.print("  sudo reboot")

    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]Error during apply-name: {e}[/red]")
        console.print("[yellow]Attempting to restart service...[/yellow]")
        subprocess.run(["sudo", "systemctl", "start", "hearth"])
        sys.exit(1)


@cli.command()
@click.argument('message')
@click.pass_context
def ask(ctx, message):
    """Send a quick message (non-interactive)."""
    config = ctx.obj['config']

    from agents.sonnet import SonnetAgent

    agent = SonnetAgent(config)
    response = agent.converse(message)

    console.print(response.content)


@cli.command()
@click.pass_context  
def identity(ctx):
    """Show current identity files."""
    config = ctx.obj['config']
    
    from core.identity import Identity
    
    ident = Identity(config)

    console.print(Panel(ident.get_soul(), title="soul.md"))
    console.print(Panel(ident.get_user(), title="user.md"))


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
