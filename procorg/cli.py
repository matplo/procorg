"""Command-line interface for ProcOrg."""

import click
import sys
import time
from pathlib import Path
from .storage import Storage
from .manager import ProcessManager
from .scheduler import Scheduler


storage = Storage()
manager = ProcessManager(storage)
scheduler = Scheduler(storage, manager)


@click.group()
def cli():
    """ProcOrg - Process Orchestration and Management Tool"""
    pass


@cli.command()
@click.argument('name')
@click.argument('script_path', type=click.Path(exists=True))
@click.option('--cron', help='Cron expression for scheduling (e.g., "0 */2 * * *")')
@click.option('--description', default='', help='Description of the process')
def register(name, script_path, cron, description):
    """Register a new process."""
    script_path = Path(script_path).absolute()
    storage.register_process(name, str(script_path), cron, description)
    click.echo(f"Process '{name}' registered successfully")

    if cron:
        click.echo(f"Scheduled with cron expression: {cron}")


@cli.command()
@click.argument('name')
def unregister(name):
    """Remove a process from the registry."""
    if storage.unregister_process(name):
        click.echo(f"Process '{name}' unregistered successfully")
    else:
        click.echo(f"Process '{name}' not found", err=True)
        sys.exit(1)


@cli.command()
def list():
    """List all registered processes."""
    processes = storage.list_processes()

    if not processes:
        click.echo("No processes registered")
        return

    click.echo(f"\n{'Name':<20} {'Status':<10} {'Cron':<20} {'Script'}")
    click.echo("-" * 80)

    for proc in processes:
        name = proc['name']
        status_info = manager.get_process_status(name)
        status = 'running' if status_info['running'] else 'idle'
        cron = proc.get('cron_expr') or '-'
        script = proc['script_path']

        click.echo(f"{name:<20} {status:<10} {cron:<20} {script}")


@cli.command()
@click.argument('name')
def run(name):
    """Manually run a process."""
    click.echo(f"Starting process '{name}'...")
    execution = manager.run_process(name)

    if execution:
        click.echo(f"Process started with PID {execution.pid}")
        click.echo(f"Execution ID: {execution.execution_id}")
    else:
        click.echo(f"Failed to start process '{name}'", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
def stop(name):
    """Stop a running process."""
    click.echo(f"Stopping process '{name}'...")

    if manager.stop_process(name):
        click.echo(f"Process '{name}' stopped")
    else:
        click.echo(f"Process '{name}' is not running or failed to stop", err=True)


@cli.command()
@click.argument('name', required=False)
def status(name):
    """Show status of processes."""
    if name:
        # Show detailed status for a specific process
        process = storage.get_process(name)
        if not process:
            click.echo(f"Process '{name}' not found", err=True)
            sys.exit(1)

        status_info = manager.get_process_status(name)

        click.echo(f"\nProcess: {name}")
        click.echo(f"Script: {process['script_path']}")
        click.echo(f"Cron: {process.get('cron_expr', 'None')}")
        click.echo(f"Enabled: {process.get('enabled', True)}")
        click.echo(f"Total executions: {status_info['total_executions']}")

        if status_info['latest_execution']:
            latest = status_info['latest_execution']
            click.echo(f"\nLatest execution:")
            click.echo(f"  ID: {latest['execution_id']}")
            click.echo(f"  Status: {latest['status']}")
            click.echo(f"  PID: {latest['pid']}")
            click.echo(f"  Start: {latest['start_time']}")
            click.echo(f"  End: {latest['end_time'] or 'running'}")
            click.echo(f"  Exit code: {latest['exit_code']}")

    else:
        # Show overview of all processes
        statuses = manager.get_all_statuses()

        if not statuses:
            click.echo("No processes registered")
            return

        click.echo(f"\n{'Name':<20} {'Status':<10} {'Last Run':<25} {'Exit Code'}")
        click.echo("-" * 80)

        for status_info in statuses:
            name = status_info['name']
            latest = status_info['latest_execution']

            if latest:
                status = latest['status']
                start_time = latest['start_time'] or 'never'
                exit_code = str(latest['exit_code']) if latest['exit_code'] is not None else '-'
            else:
                status = 'never run'
                start_time = '-'
                exit_code = '-'

            click.echo(f"{name:<20} {status:<10} {start_time:<25} {exit_code}")


@cli.command()
@click.argument('name')
@click.option('--stderr', is_flag=True, help='Show stderr instead of stdout')
@click.option('--lines', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
def logs(name, stderr, lines, follow):
    """Show logs for a process."""
    stream = 'stderr' if stderr else 'stdout'

    if follow:
        click.echo(f"Following {stream} for '{name}' (Ctrl+C to stop)...")
        last_size = 0

        try:
            while True:
                execution = manager.get_running_execution(name)
                if not execution:
                    # Check if there's a latest execution
                    status_info = manager.get_process_status(name)
                    if status_info['latest_execution']:
                        execution_id = status_info['latest_execution']['execution_id']
                        log_path = storage.get_execution_log_path(name, execution_id, stream)
                    else:
                        click.echo(f"No execution found for '{name}'")
                        break
                else:
                    log_path = storage.get_execution_log_path(name, execution.execution_id, stream)

                if log_path.exists():
                    current_size = log_path.stat().st_size
                    if current_size > last_size:
                        with open(log_path, 'r') as f:
                            f.seek(last_size)
                            new_content = f.read()
                            click.echo(new_content, nl=False)
                        last_size = current_size

                time.sleep(0.5)

        except KeyboardInterrupt:
            click.echo("\nStopped following logs")

    else:
        # Just show the latest logs
        log_content = manager.get_latest_logs(name, stream, lines)

        if log_content:
            click.echo(log_content)
        else:
            click.echo(f"No {stream} logs found for '{name}'")


@cli.command()
def scheduler_start():
    """Start the background scheduler."""
    scheduler.start()
    click.echo("Scheduler started. Press Ctrl+C to stop...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
        click.echo("\nScheduler stopped")


@cli.command()
def scheduler_info():
    """Show scheduler information."""
    info = scheduler.get_schedule_info()

    click.echo(f"\nScheduler running: {info['running']}")
    click.echo(f"\nScheduled processes:")

    if not info['scheduled_processes']:
        click.echo("  None")
    else:
        click.echo(f"\n{'Name':<20} {'Cron Expression':<20} {'Next Run'}")
        click.echo("-" * 70)

        for proc in info['scheduled_processes']:
            name = proc['name']
            cron = proc['cron_expr']
            next_run = proc['next_run'] or 'calculating...'

            click.echo(f"{name:<20} {cron:<20} {next_run}")


@cli.command()
@click.argument('name')
@click.option('--enable/--disable', default=True)
def toggle(name, enable):
    """Enable or disable a process."""
    if storage.update_process(name, enabled=enable):
        status = "enabled" if enable else "disabled"
        click.echo(f"Process '{name}' {status}")
    else:
        click.echo(f"Process '{name}' not found", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
