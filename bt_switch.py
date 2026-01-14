#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "cyclopts",
#     "loguru",
#     "platformdirs",
#     "pydantic",
# ]
# ///

import os
import socket
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Literal

from cyclopts import App
from loguru import logger
from platformdirs import user_config_path
from pydantic import BaseModel, ValidationError

class Device(BaseModel):
    mac: str
    name: str

class Host(BaseModel):
    address: str
    user: str
    protocol: Literal["ssh"]

class DefaultSettings(BaseModel):
    default_device: str
    default_target: str

class AppConfig(BaseModel):
    devices: dict[str, Device]
    hosts: dict[str, Host]
    defaults: dict[str, DefaultSettings]

class BluetoothController:
    def __init__(self, config: AppConfig):
        self.config = config
        self.hostname = socket.gethostname()
        self.logger = logger.bind(host=self.hostname)
        self._env = os.environ.copy()
        self._env["LC_ALL"] = "C"

    def _get_runner(self, target_host_alias: str) -> list[str]:
        if target_host_alias == self.hostname:
            return []
        
        if target_host_alias not in self.config.hosts:
            self.logger.error(f"Host alias '{target_host_alias}' not found in config.")
            sys.exit(1)

        host_cfg = self.config.hosts[target_host_alias]
        return [
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "LogLevel=ERROR",
            f"{host_cfg.user}@{host_cfg.address}"
        ]

    def run_bluetoothctl(self, target_host_alias: str, args: list[str], timeout: int = 10) -> bool:
        runner = self._get_runner(target_host_alias)
        cmd = runner + ["bluetoothctl", *args]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False,
                timeout=timeout,
                env=self._env
            )
            if result.returncode != 0:
                self.logger.warning(f"Cmd failed: {cmd} | Stderr: {result.stderr.strip()}")
                return False
            return True
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout ({timeout}s) expired for: {cmd}")
            return False
        except subprocess.SubprocessError as e:
            self.logger.error(f"Execution failed: {e}")
            sys.exit(1)

    def is_connected(self, target_host_alias: str, mac: str) -> bool:
        runner = self._get_runner(target_host_alias)
        cmd = runner + ["bluetoothctl", "info", mac]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
                env=self._env
            )
            return "Connected: yes" in result.stdout
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout checking status on {target_host_alias}")
            return False
        except subprocess.SubprocessError:
            return False

    def disconnect(self, target_host_alias: str, mac: str) -> bool:
        self.logger.info(f"Disconnecting {mac} from {target_host_alias}...")
        return self.run_bluetoothctl(target_host_alias, ["disconnect", mac], timeout=8)

    def connect(self, target_host_alias: str, mac: str) -> bool:
        self.logger.info(f"Connecting {mac} to {target_host_alias}...")
        return self.run_bluetoothctl(target_host_alias, ["connect", mac], timeout=15)

app = App(name="bt-switch")

@app.default
def switch(target: str | None = None, device: str | None = None):
    config_dir = user_config_path("bt_switch")
    config_file = config_dir / "config.toml"
    
    if not config_file.exists():
        logger.error(f"Configuration file not found at {config_file}")
        sys.exit(1)

    try:
        with config_file.open("rb") as f:
            data = tomllib.load(f)
        config = AppConfig.model_validate(data)
    except (ValidationError, tomllib.TOMLDecodeError) as e:
        logger.error(f"Invalid configuration format: {e}")
        sys.exit(1)

    hostname = socket.gethostname()
    
    if hostname not in config.defaults:
        logger.error(f"Current hostname '{hostname}' not configured in [defaults].")
        sys.exit(1)

    defaults = config.defaults[hostname]
    target_alias = target or defaults.default_target
    device_alias = device or defaults.default_device

    if device_alias not in config.devices:
        logger.error(f"Device '{device_alias}' not found in config.")
        sys.exit(1)
    
    device_obj = config.devices[device_alias]
    mac = device_obj.mac
    
    controller = BluetoothController(config)
    
    local_connected = controller.is_connected(hostname, mac)
    
    if local_connected:
        logger.info(f"STATUS: {device_obj.name} is connected LOCALLY.")
        logger.info(f"ACTION: Moving to {target_alias}.")
        
        if controller.disconnect(hostname, mac):
            if controller.connect(target_alias, mac):
                logger.success(f"Successfully moved to {target_alias}")
            else:
                logger.error(f"Failed to connect to {target_alias}. Reconnecting locally...")
                controller.connect(hostname, mac)
    else:
        logger.info(f"STATUS: {device_obj.name} is NOT connected locally.")
        logger.info("ACTION: Pulling to LOCAL.")
        
        controller.disconnect(target_alias, mac)
        
        if controller.connect(hostname, mac):
            logger.success("Successfully pulled to local machine.")
        else:
            logger.error("Failed to connect locally.")
            sys.exit(1)

if __name__ == "__main__":
    app()
