#!/usr/bin/env python3
import argparse
import socket
import subprocess
import sys

HEADPHONES_MAC = "00:00:00:00:00:00"
HEADPHONES_NAME = "BlueTooth Headphones"

DEFAULT_PEERS = {
    "peer-1": "peer-2",
    "peer-2": "peer-1",
}

class BluetoothService:
    def run_command(self, cmd: list[str], timeout: int = 5) -> str:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            if result.returncode != 0:
                return ""
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            print(f"Timeout expired for command: {' '.join(cmd)}")
            return ""
        except FileNotFoundError:
            print(f"Command not found: {cmd[0]}")
            return ""

    def is_connected_local(self, mac: str) -> bool:
        output = self.run_command(["bluetoothctl", "info", mac])
        return "Connected: yes" in output

    def connect_local(self, mac: str) -> bool:
        print(f"Connecting locally to {mac}...")
        output = self.run_command(["bluetoothctl", "connect", mac], timeout=10)
        return "Connection successful" in output

    def disconnect_local(self, mac: str) -> bool:
        print(f"Disconnecting locally from {mac}...")
        output = self.run_command(["bluetoothctl", "disconnect", mac], timeout=5)
        return "Successful disconnected" in output or "not available" in output

    def connect_remote(self, host: str, mac: str) -> bool:
        print(f"Triggering remote connect on {host}...")
        cmd = [
            "ssh",
            "-o", "ConnectTimeout=2",
            "-o", "StrictHostKeyChecking=no",
            host,
            "bluetoothctl", "connect", mac
        ]
        output = self.run_command(cmd, timeout=12)
        return "Connection successful" in output

    def disconnect_remote(self, host: str, mac: str) -> bool:
        print(f"Triggering remote disconnect on {host}...")
        cmd = [
            "ssh",
            "-o", "ConnectTimeout=2",
            "-o", "StrictHostKeyChecking=no",
            host,
            "bluetoothctl", "disconnect", mac
        ]
        output = self.run_command(cmd, timeout=7)
        return "Successful" in output or "not available" in output or output == ""

class SwitchManager:
    def __init__(self, service: BluetoothService):
        self.service = service
        self.hostname = socket.gethostname()

    def determine_target(self, target_arg: str | None) -> str | None:
        if target_arg:
            return target_arg
        return DEFAULT_PEERS.get(self.hostname)

    def execute(self, target_arg: str | None = None) -> None:
        target = self.determine_target(target_arg)
        
        if not target:
            print(f"Error: No default peer configured for '{self.hostname}' and no target specified.")
            sys.exit(1)

        print(f"Current Host: {self.hostname}")
        print(f"Target Peer: {target}")

        local_connected = self.service.is_connected_local(HEADPHONES_MAC)

        if local_connected:
            print(f"Status: Headphones connected locally. Action: PUSH to {target}.")
            self.service.disconnect_local(HEADPHONES_MAC)
            if target != "none":
                self.service.connect_remote(target, HEADPHONES_MAC)
        else:
            print(f"Status: Headphones not connected locally. Action: PULL from {target}.")
            if target != "none":
                self.service.disconnect_remote(target, HEADPHONES_MAC)
            self.service.connect_local(HEADPHONES_MAC)

def main():
    parser = argparse.ArgumentParser(description="Switch Bluetooth headphones between hosts.")
    parser.add_argument("target", nargs="?", help="Target hostname to switch to/from")
    args = parser.parse_args()

    service = BluetoothService()
    manager = SwitchManager(service)
    
    try:
        manager.execute(args.target)
    except KeyboardInterrupt:
        sys.exit(130)

if __name__ == "__main__":
    main()
