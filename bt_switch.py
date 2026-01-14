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

import abc
import os
import shlex
import socket
import subprocess
import sys
from typing import Literal

import tomllib
from cyclopts import App
from loguru import logger
from platformdirs import user_config_path
from pydantic import BaseModel, ValidationError


class BtSwitchError(Exception):
    pass

class ExecutionError(BtSwitchError):
    def __init__(self, cmd: list[str], stderr: str):
        self.cmd = cmd
        self.stderr = stderr
        super().__init__(f"Command failed: {shlex.join(cmd)}\nError: {stderr}")

class ConfigurationError(BtSwitchError):
    pass

class Device(BaseModel):
    mac: str
    name: str

class Host(BaseModel):
    address: str
    user: str
    protocol: Literal["ssh", "local"] = "ssh"
    driver_type: Literal["bluez", "macos"] = "bluez"

class DefaultSettings(BaseModel):
    default_device: str
    default_target: str

class AppConfig(BaseModel):
    devices: dict[str, Device]
    hosts: dict[str, Host]
    defaults: dict[str, DefaultSettings]

class Executor(abc.ABC):
    @abc.abstractmethod
    def run(self, cmd: list[str], timeout: int = 10) -> str:
        pass

class LocalExecutor(Executor):
    def run(self, cmd: list[str], timeout: int = 10) -> str:
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
                env=env
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise ExecutionError(cmd, f"Timed out after {timeout}s")
        except subprocess.CalledProcessError as e:
            raise ExecutionError(cmd, e.stderr.strip())

class SshExecutor(Executor):
    def __init__(self, host: Host):
        self.host = host

    def run(self, cmd: list[str], timeout: int = 10) -> str:
        ssh_cmd = [
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=no",
            "-o", "LogLevel=ERROR",
            f"{self.host.user}@{self.host.address}",
            "--",
            shlex.join(cmd)
        ]
        
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
                env=env
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise ExecutionError(ssh_cmd, f"SSH Timed out after {timeout}s")
        except subprocess.CalledProcessError as e:
            raise ExecutionError(ssh_cmd, e.stderr.strip())

class BluetoothDriver(abc.ABC):
    def __init__(self, executor: Executor):
        self.executor = executor

    @abc.abstractmethod
    def is_connected(self, mac: str) -> bool:
        pass

    @abc.abstractmethod
    def connect(self, mac: str) -> None:
        pass

    @abc.abstractmethod
    def disconnect(self, mac: str) -> None:
        pass

class BluezDriver(BluetoothDriver):
    def is_connected(self, mac: str) -> bool:
        try:
            output = self.executor.run(["bluetoothctl", "info", mac], timeout=5)
            return "Connected: yes" in output
        except ExecutionError:
            return False

    def connect(self, mac: str) -> None:
        self.executor.run(["bluetoothctl", "connect", mac], timeout=15)

    def disconnect(self, mac: str) -> None:
        try:
            self.executor.run(["bluetoothctl", "disconnect", mac], timeout=8)
        except ExecutionError as e:
            if "not available" in e.stderr.lower():
                return
            raise

class DriverFactory:
    @staticmethod
    def create(host_config: Host, is_local: bool) -> BluetoothDriver:
        executor: Executor
        if is_local:
            executor = LocalExecutor()
        elif host_config.protocol == "ssh":
            executor = SshExecutor(host_config)
        else:
            raise ConfigurationError(f"Unsupported protocol: {host_config.protocol}")

        if host_config.driver_type == "bluez":
            return BluezDriver(executor)
        
        raise ConfigurationError(f"Unsupported driver: {host_config.driver_type}")

class SwitchService:
    def __init__(self, local_driver: BluetoothDriver, remote_driver: BluetoothDriver, device: Device, target_name: str):
        self.local = local_driver
        self.remote = remote_driver
        self.device = device
        self.target_name = target_name

    def run(self):
        logger.info(f"Checking connection status for {self.device.name} ({self.device.mac})...")
        
        if self.local.is_connected(self.device.mac):
            self._handle_push()
        else:
            self._handle_pull()

    def _handle_push(self):
        logger.info("Device connected locally. Initiating PUSH.")
        
        logger.info("Disconnecting local...")
        self.local.disconnect(self.device.mac)
        
        try:
            logger.info(f"Connecting remote ({self.target_name})...")
            self.remote.connect(self.device.mac)
            logger.success(f"Successfully pushed to {self.target_name}")
        except ExecutionError as e:
            logger.error(f"Failed to connect remote: {e.stderr}")
            logger.warning("Reverting local connection...")
            self.local.connect(self.device.mac)

    def _handle_pull(self):
        logger.info(f"Device not local. Initiating PULL from {self.target_name}.")
        
        try:
            logger.debug(f"Ensuring disconnect on {self.target_name}...")
            self.remote.disconnect(self.device.mac)
        except ExecutionError:
            logger.warning(f"Could not verify disconnect on {self.target_name}, proceeding anyway.")

        logger.info("Connecting local...")
        self.local.connect(self.device.mac)
        logger.success("Successfully pulled to local machine")

app = App(name="bt-switch")

def load_config() -> AppConfig:
    config_path = user_config_path("bt_switch") / "config.toml"
    if not config_path.exists():
        raise ConfigurationError(f"Config not found at {config_path}")
    
    try:
        with config_path.open("rb") as f:
            return AppConfig.model_validate(tomllib.load(f))
    except (ValidationError, tomllib.TOMLDecodeError) as e:
        raise ConfigurationError(f"Config parse error: {e}")

@app.default
def entry_point(target: str | None = None, device: str | None = None):
    try:
        config = load_config()
        hostname = socket.gethostname()

        if hostname not in config.defaults:
            raise ConfigurationError(f"Hostname '{hostname}' not in [defaults]")
        
        defaults = config.defaults[hostname]
        target_alias = target or defaults.default_target
        device_alias = device or defaults.default_device

        if target_alias not in config.hosts:
            raise ConfigurationError(f"Target '{target_alias}' not in [hosts]")
        if device_alias not in config.devices:
            raise ConfigurationError(f"Device '{device_alias}' not in [devices]")

        device_obj = config.devices[device_alias]
        remote_host_cfg = config.hosts[target_alias]
        
        # Self-targeting check
        if remote_host_cfg.address == hostname: 
             # Logic could support switching between adapters on same host, 
             # but for now we treat 'target=self' as invalid or no-op
             logger.warning("Target is localhost. Nothing to switch.")
             return

        local_driver = DriverFactory.create(
            Host(address="localhost", user="", protocol="local", driver_type="bluez"), 
            is_local=True
        )
        remote_driver = DriverFactory.create(
            remote_host_cfg, 
            is_local=False
        )

        service = SwitchService(local_driver, remote_driver, device_obj, target_alias)
        service.run()

    except BtSwitchError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)

if __name__ == "__main__":
    app()
