import argparse
import os
import signal
import sys
import time
from typing import Dict

from rx.client.commands import command
from rx.daemon import client
from rx.daemon import manager
from rx.daemon import pidfile


class DaemonCommand(command.Command):
  """General daemon management command parent class."""

  def __init__(self, cmdline: command.CommandLine) -> None:
    super().__init__(cmdline)
    self._pidfile = pidfile.PidFile(self.local_config.cwd)
    self._manager = manager.DaemonManager(self.local_config)


class StartCommand(DaemonCommand):
  """Starts the daemon."""

  def _run(self) -> int:
    """Starts the daemon."""
    if self._pidfile.is_running():
      print('Daemon seems to already be running.')
      return 0

    return 0 if self._manager.start_daemon() else -1


class StopCommand(DaemonCommand):
  """Stops the daemon."""

  def _run(self) -> int:
    # Try to kill by pid, if we know it.
    done = False
    try:
      pid = self._pidfile.pid
      done = self.kill_by_pid(pid)
      if not done:
        print(f'Could not find process {pid}, attempting to connect to the '
              'daemon.')
    except pidfile.NotFoundError:
      nice_path = self._pidfile.filename.relative_to(self.local_config.cwd)
      print(f'Could not find {nice_path}, is the daemon still running?')

    # If that didn't work/we didn't have the pid, kill via sending a request
    # and getting its pid that way.
    if not done:
      try:
        done = self._manager.connect_and_kill()
      except client.RetryError:
        # This is raised if the daemon was sent a kill signal, presumably
        # successfully.
        done = True
      if not done:
        print(
          'Couldn\'t connect to the daemon, maybe a different process is '
          f'running at {self._manager.daemon_addr}.')
        return -1
    return 0

  def kill_by_pid(self, pid: int) -> bool:
    try:
      sys.stdout.write(f'Stopping daemon process {pid}...')
      os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
      # Process isn't running, remove the pid file for it.
      self._pidfile.delete()
      print(' not found.')
      return False
    print(' stopped.')
    return True


class RestartCommand(StopCommand):
  """Stops the currently running daemon and starts it again."""

  def _run(self) -> int:
    """Starts the daemon."""
    result = super()._run()
    if result != 0:
      # Maybe we don't care if we couldn't stop, maybe it wasn't running?
      print('Unable to stop daemon, attempting to start a new one anyway.')
    # I don't trust it to actually free ports immediately.
    time.sleep(2)
    return 0 if self._manager.start_daemon() else -1


class InfoCommand(DaemonCommand):
  """Returns if the daemon is running and on which port."""

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


def add_parser(subparsers: argparse._SubParsersAction):
  daemon_cmd = subparsers.add_parser(
    'daemon', help='Daemon management commands')
  subparsers = daemon_cmd.add_subparsers(required=True)

  start_cmd = subparsers.add_parser('start', help='Starts the daemon')
  start_cmd.set_defaults(cmd=StartCommand)

  stop_cmd = subparsers.add_parser('stop', help='Stops the daemon')
  stop_cmd.set_defaults(cmd=StopCommand)

  status_cmd = subparsers.add_parser('info', help='Gets info about the daemon')
  status_cmd.set_defaults(cmd=InfoCommand)

  status_cmd = subparsers.add_parser('restart', help='Restarts the daemon')
  status_cmd.set_defaults(cmd=RestartCommand)
