#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "dotenv",
#   "cyclopts",
# ]
# ///

import json
import os
import subprocess
import sys
from pathlib import Path

from cyclopts import App
from dotenv import load_dotenv

script_dir = Path(__file__).resolve().parent
dotenv_path = script_dir / ".env"

load_dotenv(dotenv_path=dotenv_path)

DEFAULT_TARGET = os.getenv("DEFAULT_EXIT_NODE", None)

app = App()

def run_cmd(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(args)}")
        print(f"Stderr: {e.stderr}")
        sys.exit(1)

def get_prefs() -> dict:
    output = run_cmd(["tailscale", "debug", "prefs"])
    return json.loads(output)

@app.default
def toggle(target: str = DEFAULT_TARGET):
    """
    Toggles Tailscale Exit Node connection.
    
    If currently connected to an exit node:
      - Disconnects.
      - Re-enables '--advertise-exit-node' (Server Mode).
      
    If currently disconnected:
      - Disables '--advertise-exit-node'.
      - Connects to the TARGET exit node (Client Mode).

    """
    prefs = get_prefs()
    current_exit_node = prefs.get("ExitNodeID")

    if current_exit_node:
        print(f"Currently connected to exit node ID: {current_exit_node}")
        print("Disconnecting and restoring Server Mode...")
        
        # 1. Clear exit node
        run_cmd(["tailscale", "set", "--exit-node="])
        
        # 2. Re-enable advertising
        run_cmd(["tailscale", "set", "--advertise-exit-node=true"])
        
        print("✅ Disconnected. You are now advertising as an exit node again.")

    else:
        if target is None:
            print("ERROR: Please provide an exit node, or register DEFAULT_EXIT_NODE in the .env file.")
            return

        print(f"No exit node active. Connecting to '{target}'...")
        print("Disabling Server Mode to prevent routing conflicts...")

        # 1. Disable advertising first (Critical for Linux)
        run_cmd(["tailscale", "set", "--advertise-exit-node=false"])

        # 2. Connect to exit node with LAN access
        run_cmd([
            "tailscale", "set", 
            f"--exit-node={target}", 
            "--exit-node-allow-lan-access=true"
        ])
        
        print(f"✅ Connected to {target}. LAN access enabled.")

if __name__ == "__main__":
    app()
