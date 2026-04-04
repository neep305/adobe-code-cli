"""Web UI server management commands."""

import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

import typer
from rich.console import Console
from rich.panel import Panel

from adobe_experience.cli.command_metadata import (
    CommandCategory,
    command_metadata,
    register_command_group_metadata,
)

console = Console()
web_app = typer.Typer(help="Web UI server management commands")

# Register command group metadata
register_command_group_metadata("web", CommandCategory.API, "Web UI server management")


class WebServerManager:
    """Manages web server processes and lifecycle."""

    def __init__(self):
        """Initialize web server manager."""
        self.adobe_dir = Path.home() / ".adobe"
        self.pid_dir = self.adobe_dir / "web" / "pids"
        self.log_dir = self.adobe_dir / "web" / "logs"
        
        # Find web directory relative to this file
        # cli/web.py -> cli -> adobe_experience -> src -> root -> web
        self.web_dir = Path(__file__).parent.parent.parent.parent / "web"
        
        # Create directories if they don't exist
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def is_port_in_use(self, port: int, host: str = "localhost") -> bool:
        """Check if a port is already in use.
        
        Args:
            port: Port number to check
            host: Host to check (default: localhost)
            
        Returns:
            True if port is in use
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result == 0
        except Exception:
            return False

    def save_pid(self, service: str, pid: int) -> None:
        """Save process ID to file.
        
        Args:
            service: Service name (backend, frontend)
            pid: Process ID
        """
        pid_file = self.pid_dir / f"{service}.pid"
        pid_file.write_text(str(pid))

    def load_pid(self, service: str) -> Optional[int]:
        """Load process ID from file.
        
        Args:
            service: Service name (backend, frontend)
            
        Returns:
            Process ID or None if not found
        """
        pid_file = self.pid_dir / f"{service}.pid"
        if not pid_file.exists():
            return None
        
        try:
            return int(pid_file.read_text().strip())
        except (ValueError, FileNotFoundError):
            return None

    def delete_pid(self, service: str) -> None:
        """Delete PID file.
        
        Args:
            service: Service name
        """
        pid_file = self.pid_dir / f"{service}.pid"
        if pid_file.exists():
            pid_file.unlink()

    def is_process_running(self, pid: int) -> bool:
        """Check if a process is running.
        
        Args:
            pid: Process ID
            
        Returns:
            True if process is running
        """
        try:
            # On Windows, use tasklist to check
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True
                )
                return str(pid) in result.stdout
            else:
                # On Unix, send signal 0
                os.kill(pid, 0)
                return True
        except (OSError, subprocess.SubprocessError):
            return False

    def stop_process(self, pid: int, timeout: int = 10) -> bool:
        """Stop a process by PID.
        
        Args:
            pid: Process ID
            timeout: Seconds to wait before force kill
            
        Returns:
            True if stopped successfully
        """
        try:
            if sys.platform == "win32":
                # On Windows, use taskkill
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=timeout
                )
            else:
                # On Unix, send SIGTERM then SIGKILL
                os.kill(pid, signal.SIGTERM)
                
                # Wait for process to exit
                for _ in range(timeout):
                    if not self.is_process_running(pid):
                        return True
                    time.sleep(1)
                
                # Force kill if still running
                os.kill(pid, signal.SIGKILL)
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]Warning: Error stopping process {pid}: {e}[/yellow]")
            return False


# Global manager instance
_manager = WebServerManager()


@command_metadata(CommandCategory.API, "Start web UI server")
@web_app.command("start")
def start_web(
    backend_port: int = typer.Option(8000, "--backend-port", "-bp", help="Backend port"),
    detach: bool = typer.Option(True, "--detach/-d", help="Run in background"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
) -> None:
    """Start the web UI server in standalone mode.
    
    Examples:
        aep web start                   # Start server on port 8000
        aep web start --backend-port 8080  # Use custom port
        aep web start --no-browser      # Don't open browser automatically
    """
    if _manager.is_port_in_use(backend_port):
        console.print(f"[yellow]Warning: Port {backend_port} is already in use[/yellow]")
        console.print("Backend server may already be running")
        raise typer.Exit(1)
    
    frontend_index = _manager.web_dir / "frontend" / "out" / "index.html"
    frontend_ready = frontend_index.is_file()

    console.print(Panel.fit(
        "[bold cyan]Starting Adobe AEP Web UI[/bold cyan]\n\n"
        "[OK] No Docker required\n"
        "[OK] SQLite database (lightweight)\n"
        "[OK] Memory cache\n"
        + (
            "[OK] Static frontend found (web/frontend/out)\n"
            if frontend_ready
            else "[yellow]![/yellow] Frontend build missing — run: [bold]cd web/frontend && npm run build[/bold]\n"
        )
        + "[dim](Node.js only needed once to build the UI)[/dim]",
        title="Adobe AEP Web UI",
        border_style="cyan"
    ))
    
    # Set environment variables for standalone mode
    env = os.environ.copy()
    env["WEB_MODE"] = "standalone"
    env["CACHE_BACKEND"] = "memory"
    env["DATABASE_URL"] = "sqlite+aiosqlite:///.adobe/web/aep.db"
    
    backend_dir = _manager.web_dir / "backend" / "app"
    if not backend_dir.exists():
        console.print(f"[red]Error: Backend directory not found at {backend_dir}[/red]")
        raise typer.Exit(1)
    
    log_file = _manager.log_dir / "backend.log"
    
    try:
        with console.status("[bold blue]Starting backend server..."):
            if detach:
                # Start in background
                with open(log_file, "w") as f:
                    # Use web/backend as cwd and run app.main:app
                    backend_parent = _manager.web_dir / "backend"
                    process = subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "app.main:app", 
                         "--host", "0.0.0.0", "--port", str(backend_port)],
                        cwd=str(backend_parent),
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        env=env,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                    )
                backend_pid = process.pid
                _manager.save_pid("backend", backend_pid)
                
                # Wait for server to start
                time.sleep(3)
                
                console.print(f"[green][OK][/green] Backend started (PID: {backend_pid})")
            else:
                # Start in foreground
                console.print(f"\n[cyan]Starting backend on port {backend_port}...[/cyan]")
                backend_parent = _manager.web_dir / "backend"
                process = subprocess.run(
                    [sys.executable, "-m", "uvicorn", "app.main:app",
                     "--host", "0.0.0.0", "--port", str(backend_port), "--reload"],
                    cwd=str(backend_parent),
                    env=env
                )
                raise typer.Exit(process.returncode)
            
    except Exception as e:
        console.print(f"[red]Error starting backend: {e}[/red]")
        raise typer.Exit(1)
    
    # Show URLs
    console.print()
    console.print(f"[cyan]Web UI:[/cyan] http://localhost:{backend_port}")
    console.print(f"[cyan]API Docs:[/cyan] http://localhost:{backend_port}/api/docs")
    console.print(f"[cyan]Health Check:[/cyan] http://localhost:{backend_port}/api/health")
    
    # Open browser
    if not no_browser:
        time.sleep(2)
        webbrowser.open(f"http://localhost:{backend_port}")
    
    console.print()
    console.print(Panel.fit(
        "Tips:\n\n"
        "• Use 'aep web stop' to stop the server\n"
        f"• View logs: aep web logs backend\n"
        f"• Check status: aep web status\n"
        f"• Logs are saved to: {log_file}",
        border_style="dim"
    ))


@command_metadata(CommandCategory.API, "Stop web UI server")
@web_app.command("stop")
def stop_web() -> None:
    """Stop the web UI server.
    
    Examples:
        aep web stop                    # Stop the  server
    """
    stopped = []
    
    # Stop backend
    backend_pid = _manager.load_pid("backend")
    if backend_pid and _manager.is_process_running(backend_pid):
        with console.status(f"[bold blue]Stopping backend (PID: {backend_pid})..."):
            if _manager.stop_process(backend_pid):
                stopped.append(f"Backend (PID: {backend_pid})")
                _manager.delete_pid("backend")
                console.print(f"[green][OK][/green] Backend stopped (PID: {backend_pid})")
    elif backend_pid:
        console.print(f"[yellow]Backend process (PID: {backend_pid}) is not running[/yellow]")
        _manager.delete_pid("backend")
    
    if not stopped:
        console.print("[yellow]No running services found[/yellow]")
    else:
        console.print(f"\n[green][OK][/green] Stopped: {', '.join(stopped)}")


@command_metadata(CommandCategory.API, "Check web UI server status")
@web_app.command("status")
def status_web() -> None:
    """Check the status of web UI server.
    
    Shows running status, port, and process ID.
    
    Examples:
        aep web status
    """
    console.print("\n[bold cyan]Web UI Server Status[/bold cyan]\n")
    
    # Check backend
    backend_pid = _manager.load_pid("backend")
    backend_port = 8000
    backend_running = backend_pid and _manager.is_process_running(backend_pid)
    backend_port_used = _manager.is_port_in_use(backend_port)
    
    if backend_running:
        console.print(f"  [cyan]Backend[/cyan]     [green][OK] Running[/green]  Port: {backend_port}  PID: {backend_pid}")
        
        # Show URLs
        console.print("\n[bold]Access URLs:[/bold]")
        console.print(f"  [cyan]Web UI:[/cyan]     http://localhost:{backend_port}")
        console.print(f"  [cyan]API Docs:[/cyan]   http://localhost:{backend_port}/api/docs")
        console.print(f"  [cyan]Health:[/cyan]     http://localhost:{backend_port}/api/health")
    elif backend_port_used:
        console.print(f"  [cyan]Backend[/cyan]     [green][OK] Running[/green]  Port: {backend_port}  (no PID file)")
        console.print("\n[bold]Access URLs:[/bold]")
        console.print(f"  [cyan]Web UI:[/cyan]     http://localhost:{backend_port}")
        console.print(f"  [cyan]API Docs:[/cyan]   http://localhost:{backend_port}/api/docs")
    else:
        console.print(f"  [cyan]Backend[/cyan]     [dim]✗ Stopped[/dim]  Port: {backend_port}")
        console.print("\n[dim]Use 'aep web start' to start the server[/dim]")
    
    console.print()


@command_metadata(CommandCategory.API, "View web UI server logs")
@web_app.command("logs")
def logs_web(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show"),
) -> None:
    """View logs from web UI server.
    
    Examples:
        aep web logs                    # Show backend logs
        aep web logs --follow           # Follow backend logs
        aep web logs --tail 50          # Show last 50 lines
    """
    log_file = _manager.log_dir / "backend.log"
    
    if not log_file.exists():
        console.print(f"[yellow]No log file found at {log_file}[/yellow]")
        console.print("[dim]Server may not have been started yet[/dim]")
        raise typer.Exit(1)
    
    console.print(Panel(f"[bold]Backend Logs[/bold]", style="cyan"))
    
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            
            # Show last N lines
            for line in lines[-tail:]:
                console.print(line.rstrip())
            
            # Follow mode
            if follow:
                console.print(f"\n[dim]Following logs... (Ctrl+C to stop)[/dim]\n")
                try:
                    while True:
                        line = f.readline()
                        if line:
                            console.print(line.rstrip())
                        else:
                            time.sleep(0.5)
                except KeyboardInterrupt:
                    console.print("\n[dim]Stopped following logs[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error reading logs: {e}[/red]")


@command_metadata(CommandCategory.API, "Open web UI in browser")
@web_app.command("open")
def open_web(
    target: str = typer.Argument("app", help="Target to open: app, api-docs"),
) -> None:
    """Open web UI in browser.
    
    Examples:
        aep web open            # Open frontend app
        aep web open app        # Open frontend app
        aep web open api-docs   # Open API documentation
    """
    target = target.lower()
    
    if target not in ["app", "api-docs"]:
        console.print(f"[red]Error: Invalid target '{target}'. Use: app or api-docs[/red]")
        raise typer.Exit(1)
    
    # Check if services are running
    if target == "app":
        if not _manager.is_port_in_use(3000):
            console.print("[red]Error: Frontend is not running[/red]")
            console.print("\n[yellow]Start it with:[/yellow] aep web start")
            raise typer.Exit(1)
        
        url = "http://localhost:3000"
        console.print(f"[cyan]Opening:[/cyan] {url}")
        webbrowser.open(url)
    
    elif target == "api-docs":
        if not _manager.is_port_in_use(8000):
            console.print("[red]Error: Backend is not running[/red]")
            console.print("\n[yellow]Start it with:[/yellow] aep web start")
            raise typer.Exit(1)
        
        url = "http://localhost:8000/api/docs"
        console.print(f"[cyan]Opening:[/cyan] {url}")
        webbrowser.open(url)
