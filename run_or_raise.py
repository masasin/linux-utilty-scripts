#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "pytest",
# ]
# ///
import sys
import shlex
import subprocess
from dataclasses import dataclass
from typing import NoReturn, Optional
from unittest.mock import MagicMock, patch
import pytest

@dataclass(frozen=True)
class AppConfig:
    launch_id: str
    search_flag: str
    search_pattern: str

class WindowManager:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def find_windows(self, flag: str, pattern: str) -> list[str]:
        cmd = ["kdotool", "search", flag, pattern]
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False
            )
            return result.stdout.strip().splitlines()
        except FileNotFoundError:
            # If kdotool is missing, fail silently or with stderr specific to the env
            # shortcuts often swallow stderr, but exit code 1 is standard.
            sys.exit(1)

    def activate_window(self, window_id: str) -> None:
        if not window_id:
            return
        subprocess.run(
            ["kdotool", "windowactivate", window_id], 
            check=False
        )

    def launch_application(self, launch_id: str) -> None:
        try:
            subprocess.Popen(
                ["kstart", "--application", launch_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            sys.exit(1)

def parse_args(argv: list[str]) -> AppConfig:
    if len(argv) < 2:
        print("Usage: run-or-raise.py <desktop_file_id> [search_args]", file=sys.stderr)
        sys.exit(1)

    launch_id = argv[1]
    extra_args = argv[2:]

    match extra_args:
        case []:
            # No extra args: default to class search
            return AppConfig(launch_id, "--class", launch_id)
        
        case [arg1, arg2, *rest]:
            # Multiple arguments: Shell has already split them.
            # e.g. script id --name "My App" -> ['--name', 'My App']
            return AppConfig(launch_id, arg1, " ".join([arg2, *rest]))

        case [single_arg]:
            # Single argument: Might be a quoted string from a shortcut.
            # e.g. script id "--name 'My App'" -> ["--name 'My App'"]
            try:
                parts = shlex.split(single_arg)
            except ValueError:
                parts = single_arg.split()
            
            match parts:
                case [flag, *rest] if rest:
                    # Found flag + pattern inside the single string
                    return AppConfig(launch_id, flag, " ".join(rest))
                
                case [flag] if flag.startswith("-"):
                    # Single token starting with dash, e.g. "--class"
                    # Pattern defaults to launch_id
                    return AppConfig(launch_id, flag, launch_id)
                
                case [token]:
                    # Single token not starting with dash
                    # Treat as pattern for --class
                    return AppConfig(launch_id, "--class", token)
                
                case _:
                    # Empty or parse failure fallback
                    return AppConfig(launch_id, "--class", single_arg)
        
        case _:
            # Fallback should theoretically be unreachable given above cases
            return AppConfig(launch_id, "--class", launch_id)

def main() -> None:
    config = parse_args(sys.argv)
    manager = WindowManager()
    
    window_ids = manager.find_windows(config.search_flag, config.search_pattern)
    
    if window_ids:
        manager.activate_window(window_ids[0])
    else:
        manager.launch_application(config.launch_id)

if __name__ == "__main__":
    main()

# --- Tests ---

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock_run, \
         patch("subprocess.Popen") as mock_popen:
        mock_run.return_value.stdout = ""
        yield mock_run, mock_popen

def test_parse_args_basic():
    argv = ["script", "firefox"]
    config = parse_args(argv)
    assert config.launch_id == "firefox"
    assert config.search_flag == "--class"
    assert config.search_pattern == "firefox"

def test_parse_args_explicit_flag_shell_split():
    # Standard shell usage: script firefox --name "Mozilla Firefox"
    argv = ["script", "firefox", "--name", "Mozilla Firefox"]
    config = parse_args(argv)
    assert config.launch_id == "firefox"
    assert config.search_flag == "--name"
    assert config.search_pattern == "Mozilla Firefox"

def test_parse_args_regression_quoted_single_arg():
    # Shortcut usage: script firefox "--name 'Mozilla Firefox'"
    # This arrives as a single argument string in extra_args
    argv = ["script", "firefox", "--name 'Mozilla Firefox'"]
    config = parse_args(argv)
    assert config.launch_id == "firefox"
    assert config.search_flag == "--name"
    assert config.search_pattern == "Mozilla Firefox"

def test_parse_args_single_flag_heuristic():
    # script firefox --class
    argv = ["script", "firefox", "--class"]
    config = parse_args(argv)
    assert config.launch_id == "firefox"
    assert config.search_flag == "--class"
    assert config.search_pattern == "firefox"

def test_parse_args_simple_pattern_no_flag():
    # script firefox MyPattern (implies --class MyPattern)
    argv = ["script", "firefox", "MyPattern"]
    config = parse_args(argv)
    assert config.launch_id == "firefox"
    assert config.search_flag == "--class"
    assert config.search_pattern == "MyPattern"

def test_find_windows_success(mock_subprocess):
    mock_run, _ = mock_subprocess
    mock_run.return_value.stdout = "12345\n67890"
    
    manager = WindowManager()
    ids = manager.find_windows("--class", "firefox")
    
    assert ids == ["12345", "67890"]
    mock_run.assert_called_with(
        ["kdotool", "search", "--class", "firefox"],
        capture_output=True,
        text=True,
        check=False
    )

def test_workflow_window_exists(mock_subprocess):
    mock_run, mock_popen = mock_subprocess
    mock_run.return_value.stdout = "99999"
    
    with patch("sys.argv", ["script", "firefox"]):
        main()
    
    assert mock_run.call_count == 2 
    mock_popen.assert_not_called()

def test_workflow_launch_new(mock_subprocess):
    mock_run, mock_popen = mock_subprocess
    mock_run.return_value.stdout = ""
    
    with patch("sys.argv", ["script", "firefox"]):
        main()
        
    mock_run.assert_called_once()
    mock_popen.assert_called_once()
