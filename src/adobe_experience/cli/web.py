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

    def check_docker_available(self) -> Tuple[bool, str]:
        """Check if Docker and Docker Compose are available.
        
        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            # Check Docker
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, "Docker is not installed or not in PATH"
            
            # Check Docker Compose (try both 'docker-compose' and 'docker compose')
            compose_result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if compose_result.returncode != 0:
                # Try 'docker compose'
                compose_result = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if compose_result.returncode != 0:
                    return False, "Docker Compose is not installed"
            
            # Check if Docker daemon is running
            ps_result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if ps_result.returncode != 0:
                return False, "Docker daemon is not running. Start Docker Desktop or Docker service."
            
            return True, ""
            
        except FileNotFoundError:
            return False, "Docker is not installed or not in PATH"
        except subprocess.TimeoutExpired:
            return False, "Docker command timed out"
        except Exception as e:
            return False, f"Error checking Docker: {e}"

    def check_node_available(self) -> Tuple[bool, str]:
        """Check if Node.js and npm are available.
        
        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            # Check Node.js
            node_result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if node_result.returncode != 0:
                return False, "Node.js is not installed"
            
            node_version = node_result.stdout.strip()
            
            # Check npm
            npm_result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if npm_result.returncode != 0:
                return False, "npm is not installed"
            
            return True, ""
            
        except FileNotFoundError:
            return False, "Node.js or npm is not installed"
        except subprocess.TimeoutExpired:
            return False, "Node/npm command timed out"
        except Exception as e:
            return False, f"Error checking Node.js: {e}"

    def check_frontend_dependencies(self) -> bool:
        """Check if frontend dependencies are installed.
        
        Returns:
            True if node_modules exists
        """
        frontend_dir = self.web_dir / "frontend"
        node_modules = frontend_dir / "node_modules"
        return node_modules.exists()

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

    def start_docker(self) -> bool:
        """Start all services using Docker Compose.
        
        Returns:
            True if successful
        """
        if not self.web_dir.exists():
            console.print(f"[red]Error: Web directory not found at {self.web_dir}[/red]")
            return False
        
        compose_file = self.web_dir / "docker-compose.yml"
        if not compose_file.exists():
            console.print(f"[red]Error: docker-compose.yml not found at {compose_file}[/red]")
            return False
        
        try:
            # Try docker-compose command first
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=str(self.web_dir),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                # Try 'docker compose' (newer syntax)
                result = subprocess.run(
                    ["docker", "compose", "up", "-d"],
                    cwd=str(self.web_dir),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            
            if result.returncode != 0:
                console.print(f"[red]Error starting Docker Compose:[/red]")
                console.print(result.stderr)
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            console.print("[red]Error: Docker Compose startup timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Error starting Docker Compose: {e}[/red]")
            return False

    def stop_docker(self) -> bool:
        """Stop all Docker Compose services.
        
        Returns:
            True if successful
        """
        try:
            result = subprocess.run(
                ["docker-compose", "down"],
                cwd=str(self.web_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                # Try 'docker compose'
                result = subprocess.run(
                    ["docker", "compose", "down"],
                    cwd=str(self.web_dir),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            if result.returncode != 0:
                console.print(f"[red]Error stopping Docker Compose:[/red]")
                console.print(result.stderr)
                return False
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error stopping Docker Compose: {e}[/red]")
            return False

    def start_backend(self, port: int = 8000, detach: bool = True) -> Optional[int]:
        """Start backend server.
        
        Args:
            port: Port to run on
            detach: Run in background
            
        Returns:
            Process ID or None if failed
        """
        backend_dir = self.web_dir / "backend" / "app"
        if not backend_dir.exists():
            console.print(f"[red]Error: Backend directory not found at {backend_dir}[/red]")
            return None
        
        log_file = self.log_dir / "backend.log"
        
        try:
            if detach:
                # Start in background
                with open(log_file, "w") as f:
                    process = subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "main:app", 
                         "--host", "0.0.0.0", "--port", str(port), "--reload"],
                        cwd=str(backend_dir),
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                    )
                return process.pid
            else:
                # Start in foreground
                process = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", "main:app",
                     "--host", "0.0.0.0", "--port", str(port), "--reload"],
                    cwd=str(backend_dir)
                )
                return process.pid
                
        except Exception as e:
            console.print(f"[red]Error starting backend: {e}[/red]")
            return None

    def start_frontend(self, port: int = 3000, detach: bool = True) -> Optional[int]:
        """Start frontend server.
        
        Args:
            port: Port to run on
            detach: Run in background
            
        Returns:
            Process ID or None if failed
        """
        frontend_dir = self.web_dir / "frontend"
        if not frontend_dir.exists():
            console.print(f"[red]Error: Frontend directory not found at {frontend_dir}[/red]")
            return None
        
        log_file = self.log_dir / "frontend.log"
        
        try:
            if detach:
                # Start in background
                with open(log_file, "w") as f:
                    process = subprocess.Popen(
                        ["npm", "run", "dev", "--", "-p", str(port)],
                        cwd=str(frontend_dir),
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                    )
                return process.pid
            else:
                # Start in foreground
                process = subprocess.Popen(
                    ["npm", "run", "dev", "--", "-p", str(port)],
                    cwd=str(frontend_dir)
                )
                return process.pid
                
        except Exception as e:
            console.print(f"[red]Error starting frontend: {e}[/red]")
            return None

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
    mode: str = typer.Option(
        "docker",
        "--mode",
        "-m",
        help="Startup mode: docker, dev, backend, frontend"
    ),
    backend_port: int = typer.Option(8000, "--backend-port", "-bp", help="Backend port"),
    frontend_port: int = typer.Option(3000, "--frontend-port", "-fp", help="Frontend port"),
    detach: bool = typer.Option(True, "--detach/-d", help="Run in background"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
) -> None:
    """Start the web UI server.
    
    Examples:
        aep web start                           # Start with Docker (default)
        aep web start --mode dev                # Start backend + frontend locally
        aep web start --mode backend            # Start backend only
        aep web start --mode frontend           # Start frontend only
        aep web start --backend-port 8080       # Use custom port
        aep web start --no-browser              # Don't open browser
    """
    mode = mode.lower()
    
    if mode not in ["docker", "dev", "backend", "frontend"]:
        console.print(f"[red]Error: Invalid mode '{mode}'. Use: docker, dev, backend, or frontend[/red]")
        raise typer.Exit(1)
    
    # Check Docker for docker mode
    if mode == "docker":
        with console.status("[bold blue]Checking Docker availability..."):
            is_available, error_msg = _manager.check_docker_available()
        
        if not is_available:
            console.print(f"[red]Error: {error_msg}[/red]")
            console.print("\n[yellow]💡 Tip:[/yellow] Install Docker or use '--mode dev' for local development")
            raise typer.Exit(1)
        
        # Check if already running
        if _manager.is_port_in_use(backend_port):
            console.print(f"[yellow]Warning: Port {backend_port} is already in use[/yellow]")
            console.print("Backend server may already be running")
        
        # Start Docker Compose
        with console.status("[bold blue]Starting Docker services..."):
            success = _manager.start_docker()
        
        if not success:
            raise typer.Exit(1)
        
        console.print("[green]✓[/green] Docker services started successfully")
        console.print(f"\n[cyan]Frontend:[/cyan] http://localhost:{frontend_port}")
        console.print(f"[cyan]Backend:[/cyan] http://localhost:{backend_port}")
        console.print(f"[cyan]API Docs:[/cyan] http://localhost:{backend_port}/api/docs")
        
        # Open browser
        if not no_browser:
            time.sleep(3)  # Wait for services to be ready
            webbrowser.open(f"http://localhost:{frontend_port}")
        
        console.print("\n[dim]💡 Tip: Use 'aep web status' to check service status[/dim]")
        console.print("[dim]💡 Tip: Use 'aep web logs <service>' to view logs[/dim]")
    
    elif mode in ["dev", "backend", "frontend"]:
        # Check Node.js for frontend
        if mode in ["dev", "frontend"]:
            is_available, error_msg = _manager.check_node_available()
            if not is_available:
                console.print(f"[red]Error: {error_msg}[/red]")
                raise typer.Exit(1)
            
            # Check frontend dependencies
            if not _manager.check_frontend_dependencies():
                console.print("[red]Error: Frontend dependencies not installed[/red]")
                console.print(f"\n[yellow]Run:[/yellow] cd {_manager.web_dir / 'frontend'} && npm install")
                raise typer.Exit(1)
        
        # Start backend
        if mode in ["dev", "backend"]:
            if _manager.is_port_in_use(backend_port):
                console.print(f"[red]Error: Port {backend_port} is already in use[/red]")
                console.print("Use --backend-port to specify a different port")
                raise typer.Exit(1)
            
            with console.status("[bold blue]Starting backend server..."):
                backend_pid = _manager.start_backend(backend_port, detach)
            
            if backend_pid is None:
                raise typer.Exit(1)
            
            _manager.save_pid("backend", backend_pid)
            console.print(f"[green]✓[/green] Backend started (PID: {backend_pid}, Port: {backend_port})")
            
            # Wait for backend to be ready
            time.sleep(2)
        
        # Start frontend
        if mode in ["dev", "frontend"]:
            if _manager.is_port_in_use(frontend_port):
                console.print(f"[red]Error: Port {frontend_port} is already in use[/red]")
                console.print("Use --frontend-port to specify a different port")
                raise typer.Exit(1)
            
            with console.status("[bold blue]Starting frontend server..."):
                frontend_pid = _manager.start_frontend(frontend_port, detach)
            
            if frontend_pid is None:
                raise typer.Exit(1)
            
            _manager.save_pid("frontend", frontend_pid)
            console.print(f"[green]✓[/green] Frontend started (PID: {frontend_pid}, Port: {frontend_port})")
        
        # Show URLs
        console.print()
        if mode in ["dev", "frontend"]:
            console.print(f"[cyan]Frontend:[/cyan] http://localhost:{frontend_port}")
        if mode in ["dev", "backend"]:
            console.print(f"[cyan]Backend:[/cyan] http://localhost:{backend_port}")
            console.print(f"[cyan]API Docs:[/cyan] http://localhost:{backend_port}/api/docs")
        
        # Open browser
        if not no_browser and mode in ["dev", "frontend"]:
            time.sleep(3)
            webbrowser.open(f"http://localhost:{frontend_port}")
        
        console.print("\n[dim]💡 Tip: Use 'aep web stop' to stop servers[/dim]")
        console.print(f"[dim]💡 Tip: Logs are in {_manager.log_dir}[/dim]")


@command_metadata(CommandCategory.API, "Stop web UI server")
@web_app.command("stop")
def stop_web(
    mode: str = typer.Option(
        "all",
        "--mode",
        "-m",
        help="Stop mode: all, docker, backend, frontend"
    ),
) -> None:
    """Stop the web UI server.
    
    Examples:
        aep web stop                    # Stop all services
        aep web stop --mode docker      # Stop Docker services
        aep web stop --mode backend     # Stop backend only
        aep web stop --mode frontend    # Stop frontend only
    """
    mode = mode.lower()
    
    if mode not in ["all", "docker", "backend", "frontend"]:
        console.print(f"[red]Error: Invalid mode '{mode}'. Use: all, docker, backend, or frontend[/red]")
        raise typer.Exit(1)
    
    stopped = []
    
    # Stop Docker services
    if mode in ["all", "docker"]:
        with console.status("[bold blue]Stopping Docker services..."):
            if _manager.stop_docker():
                stopped.append("Docker services")
                console.print("[green]✓[/green] Docker services stopped")
    
    # Stop backend
    if mode in ["all", "backend"]:
        backend_pid = _manager.load_pid("backend")
        if backend_pid and _manager.is_process_running(backend_pid):
            with console.status(f"[bold blue]Stopping backend (PID: {backend_pid})..."):
                if _manager.stop_process(backend_pid):
                    stopped.append(f"Backend (PID: {backend_pid})")
                    _manager.delete_pid("backend")
                    console.print(f"[green]✓[/green] Backend stopped (PID: {backend_pid})")
        elif backend_pid:
            console.print(f"[yellow]Backend process (PID: {backend_pid}) is not running[/yellow]")
            _manager.delete_pid("backend")
    
    # Stop frontend
    if mode in ["all", "frontend"]:
        frontend_pid = _manager.load_pid("frontend")
        if frontend_pid and _manager.is_process_running(frontend_pid):
            with console.status(f"[bold blue]Stopping frontend (PID: {frontend_pid})..."):
                if _manager.stop_process(frontend_pid):
                    stopped.append(f"Frontend (PID: {frontend_pid})")
                    _manager.delete_pid("frontend")
                    console.print(f"[green]✓[/green] Frontend stopped (PID: {frontend_pid})")
        elif frontend_pid:
            console.print(f"[yellow]Frontend process (PID: {frontend_pid}) is not running[/yellow]")
            _manager.delete_pid("frontend")
    
    if not stopped:
        console.print("[yellow]No running services found[/yellow]")
    else:
        console.print(f"\n[green]✓[/green] Stopped: {', '.join(stopped)}")


@command_metadata(CommandCategory.API, "Check web UI server status")
@web_app.command("status")
def status_web() -> None:
    """Check the status of web UI services.
    
    Shows running status, ports, and process IDs.
    
    Examples:
        aep web status
    """
    console.print("\n[bold cyan]Web UI Server Status[/bold cyan]\n")
    
    services = []
    running_services = []
    
    # Check backend
    backend_pid = _manager.load_pid("backend")
    backend_port = 8000
    backend_running = backend_pid and _manager.is_process_running(backend_pid)
    backend_port_used = _manager.is_port_in_use(backend_port)
    
    if backend_running:
        services.append(f"  [cyan]Backend[/cyan]     [green]✓ Running[/green]  Port: {backend_port}  PID: {backend_pid}")
        running_services.append(("backend", backend_port))
    elif backend_port_used:
        services.append(f"  [cyan]Backend[/cyan]     [green]✓ Running[/green] (Docker)  Port: {backend_port}")
        running_services.append(("backend", backend_port))
    else:
        services.append(f"  [cyan]Backend[/cyan]     [dim]✗ Stopped[/dim]  Port: {backend_port}")
    
    # Check frontend
    frontend_pid = _manager.load_pid("frontend")
    frontend_port = 3000
    frontend_running = frontend_pid and _manager.is_process_running(frontend_pid)
    frontend_port_used = _manager.is_port_in_use(frontend_port)
    
    if frontend_running:
        services.append(f"  [cyan]Frontend[/cyan]    [green]✓ Running[/green]  Port: {frontend_port}  PID: {frontend_pid}")
        running_services.append(("frontend", frontend_port))
    elif frontend_port_used:
        services.append(f"  [cyan]Frontend[/cyan]    [green]✓ Running[/green] (Docker)  Port: {frontend_port}")
        running_services.append(("frontend", frontend_port))
    else:
        services.append(f"  [cyan]Frontend[/cyan]    [dim]✗ Stopped[/dim]  Port: {frontend_port}")
    
    # Check PostgreSQL
    postgres_port = 5432
    postgres_running = _manager.is_port_in_use(postgres_port)
    if postgres_running:
        services.append(f"  [cyan]PostgreSQL[/cyan]  [green]✓ Running[/green]  Port: {postgres_port}")
        running_services.append(("postgres", postgres_port))
    else:
        services.append(f"  [cyan]PostgreSQL[/cyan]  [dim]✗ Stopped[/dim]  Port: {postgres_port}")
    
    # Check Redis
    redis_port = 6379
    redis_running = _manager.is_port_in_use(redis_port)
    if redis_running:
        services.append(f"  [cyan]Redis[/cyan]       [green]✓ Running[/green]  Port: {redis_port}")
        running_services.append(("redis", redis_port))
    else:
        services.append(f"  [cyan]Redis[/cyan]       [dim]✗ Stopped[/dim]  Port: {redis_port}")
    
    # Print all services
    for service in services:
        console.print(service)
    
    # Show URLs if services are running
    if running_services:
        console.print("\n[bold]Access URLs:[/bold]")
        if any(s[0] == "frontend" for s in running_services):
            console.print(f"  [cyan]Frontend:[/cyan] http://localhost:{frontend_port}")
        if any(s[0] == "backend" for s in running_services):
            console.print(f"  [cyan]Backend:[/cyan]  http://localhost:{backend_port}")
            console.print(f"  [cyan]API Docs:[/cyan] http://localhost:{backend_port}/api/docs")
    
    console.print()


@command_metadata(CommandCategory.API, "View web UI server logs")
@web_app.command("logs")
def logs_web(
    service: str = typer.Argument("all", help="Service to view: backend, frontend, all"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show"),
) -> None:
    """View logs from web UI services.
    
    Examples:
        aep web logs backend            # Show backend logs
        aep web logs frontend --follow  # Follow frontend logs
        aep web logs all --tail 50      # Show last 50 lines of all logs
    """
    service = service.lower()
    
    if service not in ["backend", "frontend", "all"]:
        console.print(f"[red]Error: Invalid service '{service}'. Use: backend, frontend, or all[/red]")
        raise typer.Exit(1)
    
    services = ["backend", "frontend"] if service == "all" else [service]
    
    for svc in services:
        log_file = _manager.log_dir / f"{svc}.log"
        
        if not log_file.exists():
            console.print(f"[yellow]No log file found for {svc}[/yellow]")
            continue
        
        console.print(Panel(f"[bold]{svc.upper()} Logs[/bold]", style="cyan"))
        
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
                
                # Show last N lines
                for line in lines[-tail:]:
                    console.print(line.rstrip())
                
                # Follow mode
                if follow:
                    console.print(f"\n[dim]Following {svc} logs... (Ctrl+C to stop)[/dim]\n")
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
        
        if len(services) > 1:
            console.print()


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
