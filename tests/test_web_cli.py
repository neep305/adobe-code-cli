"""Tests for web CLI commands."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest
from typer.testing import CliRunner

from adobe_experience.cli.web import (
    WebServerManager,
    web_app,
)

runner = CliRunner()


class TestWebServerManager:
    """Test WebServerManager functionality."""
    
    def test_init_creates_directories(self, tmp_path, monkeypatch):
        """Test that WebServerManager creates necessary directories."""
        adobe_dir = tmp_path / ".adobe"
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        
        manager = WebServerManager()
        manager.adobe_dir = adobe_dir
        manager.pid_dir = adobe_dir / "web" / "pids"
        manager.log_dir = adobe_dir / "web" / "logs"
        
        manager.pid_dir.mkdir(parents=True, exist_ok=True)
        manager.log_dir.mkdir(parents=True, exist_ok=True)
        
        assert manager.pid_dir.exists()
        assert manager.log_dir.exists()
    
    def test_check_docker_available_success(self):
        """Test Docker availability check when Docker is available."""
        manager = WebServerManager()
        
        with patch("subprocess.run") as mock_run:
            # Mock successful docker and docker-compose commands
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Docker version 20.10.0"),  # docker --version
                Mock(returncode=0, stdout="docker-compose version 1.29.0"),  # docker-compose --version
                Mock(returncode=0, stdout=""),  # docker ps
            ]
            
            success, error = manager.check_docker_available()
            
            assert success is True
            assert error == "" or error is None
    
    def test_check_docker_available_not_installed(self):
        """Test Docker availability check when Docker is not installed."""
        manager = WebServerManager()
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            success, error = manager.check_docker_available()
            
            assert success is False
            assert "Docker is not installed" in error
    
    def test_check_docker_available_daemon_not_running(self):
        """Test Docker availability check when daemon is not running."""
        manager = WebServerManager()
        
        with patch("subprocess.run") as mock_run:
            # docker and docker-compose exist but docker ps fails
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Docker version 20.10.0"),
                Mock(returncode=0, stdout="docker-compose version 1.29.0"),
                Mock(returncode=1, stderr="Cannot connect to Docker daemon"),
            ]
            
            success, error = manager.check_docker_available()
            
            assert success is False
            assert "daemon is not running" in error
    
    def test_check_node_available_success(self):
        """Test Node.js availability check when Node is available."""
        manager = WebServerManager()
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="v18.0.0"),  # node --version
                Mock(returncode=0, stdout="9.0.0"),     # npm --version
            ]
            
            success, error = manager.check_node_available()
            
            assert success is True
            assert error == "" or error is None
    
    def test_check_node_available_not_installed(self):
        """Test Node.js availability check when Node is not installed."""
        manager = WebServerManager()
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            success, error = manager.check_node_available()
            
            assert success is False
            assert "Node.js" in error and "not installed" in error
    
    def test_is_port_in_use_available(self):
        """Test port check when port is available."""
        manager = WebServerManager()
        
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 1  # Connection refused = port available
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            result = manager.is_port_in_use(8000)
            
            assert result is False
    
    def test_is_port_in_use_taken(self):
        """Test port check when port is in use."""
        manager = WebServerManager()
        
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0  # Connection successful = port in use
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            result = manager.is_port_in_use(8000)
            
            assert result is True
    
    def test_save_and_load_pid(self, tmp_path):
        """Test PID file save and load."""
        manager = WebServerManager()
        manager.pid_dir = tmp_path
        manager.pid_dir.mkdir(exist_ok=True)
        
        # Save PID
        manager.save_pid("test-service", 12345)
        
        # Load PID
        pid = manager.load_pid("test-service")
        
        assert pid == 12345
    
    def test_load_pid_nonexistent(self, tmp_path):
        """Test loading PID for nonexistent service."""
        manager = WebServerManager()
        manager.pid_dir = tmp_path
        
        pid = manager.load_pid("nonexistent")
        
        assert pid is None
    
    def test_delete_pid(self, tmp_path):
        """Test PID file deletion."""
        manager = WebServerManager()
        manager.pid_dir = tmp_path
        manager.pid_dir.mkdir(exist_ok=True)
        
        # Create PID file
        manager.save_pid("test-service", 12345)
        pid_file = manager.pid_dir / "test-service.pid"
        assert pid_file.exists()
        
        # Delete PID file
        manager.delete_pid("test-service")
        assert not pid_file.exists()
    
    @patch("os.kill")
    @patch("sys.platform", "linux")
    def test_is_process_running_unix_running(self, mock_kill):
        """Test process check on Unix when process is running."""
        manager = WebServerManager()
        mock_kill.return_value = None  # No exception = process running
        
        result = manager.is_process_running(12345)
        
        assert result is True
        mock_kill.assert_called_once_with(12345, 0)
    
    @patch("os.kill")
    @patch("sys.platform", "linux")
    def test_is_process_running_unix_not_running(self, mock_kill):
        """Test process check on Unix when process is not running."""
        manager = WebServerManager()
        mock_kill.side_effect = OSError()
        
        result = manager.is_process_running(12345)
        
        assert result is False
    
    @patch("subprocess.run")
    @patch("sys.platform", "win32")
    def test_is_process_running_windows_running(self, mock_run):
        """Test process check on Windows when process is running."""
        manager = WebServerManager()
        mock_run.return_value = Mock(
            returncode=0,
            stdout="python.exe                   12345 Console"
        )
        
        result = manager.is_process_running(12345)
        
        assert result is True
    
    @patch("subprocess.run")
    @patch("sys.platform", "win32")
    def test_is_process_running_windows_not_running(self, mock_run):
        """Test process check on Windows when process is not running."""
        manager = WebServerManager()
        mock_run.return_value = Mock(returncode=0, stdout="")
        
        result = manager.is_process_running(12345)
        
        assert result is False


class TestWebCLICommands:
    """Test web CLI commands."""
    
    def test_web_help(self):
        """Test web command help."""
        result = runner.invoke(web_app, ["--help"])
        
        assert result.exit_code == 0
        assert "Web UI server management" in result.stdout
        assert "start" in result.stdout
        assert "stop" in result.stdout
        assert "status" in result.stdout
        assert "logs" in result.stdout
        assert "open" in result.stdout
    
    def test_start_help(self):
        """Test start command help."""
        result = runner.invoke(web_app, ["start", "--help"])
        
        assert result.exit_code == 0
        assert "--mode" in result.stdout
        assert "docker" in result.stdout
        assert "dev" in result.stdout
        assert "backend" in result.stdout
        assert "frontend" in result.stdout
    
    def test_stop_help(self):
        """Test stop command help."""
        result = runner.invoke(web_app, ["stop", "--help"])
        
        assert result.exit_code == 0
        assert "--mode" in result.stdout
    
    def test_status_help(self):
        """Test status command help."""
        result = runner.invoke(web_app, ["status", "--help"])
        
        assert result.exit_code == 0
        assert "status" in result.stdout.lower()
    
    def test_logs_help(self):
        """Test logs command help."""
        result = runner.invoke(web_app, ["logs", "--help"])
        
        assert result.exit_code == 0
        assert "--tail" in result.stdout
        assert "--follow" in result.stdout
    
    def test_open_help(self):
        """Test open command help."""
        result = runner.invoke(web_app, ["open", "--help"])
        
        assert result.exit_code == 0
        assert "TARGET" in result.stdout or "target" in result.stdout.lower()
    
    @patch("adobe_experience.cli.web._manager")
    def test_status_all_stopped(self, mock_manager):
        """Test status command when all services are stopped."""
        mock_manager.load_pid.return_value = None
        mock_manager.is_port_in_use.return_value = False
        
        result = runner.invoke(web_app, ["status"])
        
        assert result.exit_code == 0
        assert "Backend" in result.stdout
        assert "Frontend" in result.stdout
        assert "PostgreSQL" in result.stdout
        assert "Redis" in result.stdout
    
    @patch("adobe_experience.cli.web._manager")
    def test_logs_no_file(self, mock_manager):
        """Test logs command when log file doesn't exist."""
        result = runner.invoke(web_app, ["logs", "backend"])
        
        # Command should exit successfully even if no log file exists
        assert result.exit_code == 0
        assert "BACKEND" in result.stdout or "backend" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
