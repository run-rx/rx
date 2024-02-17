import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
from typing import Dict

from rx.client import grpc_helper
from rx.client.commands import command
from rx.client.configuration import config_base
from rx.client.configuration import local
from rx.daemon import client
from rx.daemon import pidfile


class DaemonCommand(command.Command):
  """General daemon management command parent class."""

  def __init__(self, cmdline: command.CommandLine) -> None:
    super().__init__(cmdline)
    self._pidfile = pidfile.PidFile(self.local_config.cwd)


class StartCommand(DaemonCommand):
  """Save the current state on the remote."""

  def _run(self) -> int:
    """Starts the daemon."""
    if self._pidfile.is_running():
      print('Daemon seems to already be running.')
      return 0

    return 0 if start_daemon(self.local_config) else -1


class StopCommand(DaemonCommand):
  """Save the current state on the remote."""

  def _run(self) -> int:
    try:
      pid = self._pidfile.pid
    except pidfile.NotFoundError:
      nice_path = self._pidfile.filename.relative_to(self.local_config.cwd)
      print(f'Could not find {nice_path}, is the daemon still running?')
      return -1

    try:
      sys.stdout.write(f'Stopping daemon process {pid}...')
      os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
      # Process isn't running, remove the pid file for it.
      self._pidfile.delete()
      print(f'\nCould not find process {pid}, is daemon still running?')
      return -1

    print('stopped.')
    return 0


class InfoCommand(DaemonCommand):
  """Save the current state on the remote."""

  def _run(self) -> int:
    if not self._pidfile.is_running():
      print('Daemon is not running. Run `rx daemon start` to start it.')
    else:
      print(f'Daemon is running with pid {self._pidfile.pid}')
    return 0


def format_info(info: Dict[int, int]) -> str:
  if info:
    formatted_ports = []
    for lp, rp in info.items():
      if lp == rp:
        formatted_ports.append(f'localhost:{rp}')
      else:
        formatted_ports.append(f'{rp} -> localhost:{lp}')
    port_list = '\n'.join(formatted_ports)
    return f'Open ports:\n{port_list}'
  else:
    return 'No open ports.'


def start_daemon(local_cfg: local.LocalConfig) -> bool:
  """Starts the daemon. Returns if successful."""
  port = local_cfg.daemon_port
  trex_addr = config_base.TREX_HOST.value
  # This is a vanilla Popen: the daemon is its grandchild!
  subprocess.Popen([
    'python', '-m', 'rx.daemon.server',
    f'--port={port}',
    f'--trex-host={trex_addr}',
  ])
  print(f'Daemon started at localhost:{port}')

  # Now (try to) connect to it to make sure it's running.
  time.sleep(1)
  sys.stdout.write('Checking daemon is running...')
  daemon_addr = f'localhost:{port}'
  with grpc_helper.get_channel(daemon_addr) as ch:
    cli = client.Client(ch, local_cfg)
    tries = 5
    for _ in range(tries):
      time.sleep(1)
      if cli.is_running():
        sys.stdout.write(' Connected!\n')
        return True
      sys.stdout.write('.')
  logfile = f'{tempfile.gettempdir()}/rx-daemon.INFO'
  print(f'Unable to connect to daemon, check {logfile} for details')
  return False


def add_parser(subparsers: argparse._SubParsersAction):
  daemon_cmd = subparsers.add_parser(
    'daemon', help='Daemon management commands')
  subparsers = daemon_cmd.add_subparsers(required=True)

  start_cmd = subparsers.add_parser(
    'start', help='Starts the daemon')
  start_cmd.set_defaults(cmd=StartCommand)

  stop_cmd = subparsers.add_parser(
    'stop', help='Stops the daemon')
  stop_cmd.set_defaults(cmd=StopCommand)

  status_cmd = subparsers.add_parser(
    'info', help='Gets info about the daemon')
  status_cmd.set_defaults(cmd=InfoCommand)
